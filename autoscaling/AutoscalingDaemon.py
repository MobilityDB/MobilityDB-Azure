import time
import logging
import os
import argparse
import utils
from K8sCluster import K8sCluster
from CitusCluster import CitusCluster

from daemons.prefab import run


class AutoscalingDaemon(run.RunDaemon):

    def __init__(self, pidfile, performance_logger, minvm, maxvm, storage_path, lower_threshold, upper_threshold, metric, observations_interval):
        super().__init__(pidfile=pidfile)
        self.minvm = minvm
        self.maxvm = maxvm
        self.metric = metric
        self.observations_interval = observations_interval
        self.storage_path = storage_path
        self.performance_logger = performance_logger
        self.lower_threshold = lower_threshold
        self.upper_threshold = upper_threshold

    # Get the specified metric provided by Azure at VM level.
    def monitor_azure_metrics(self):
        return self.k8s_cluster.azure.monitor.get_azure_metric(metric="Percentage CPU", interval=self.observations_interval)

    # Get the system traffic using sessions_log table
    def monitor_with_system_traffic(self):
        return self.k8s_cluster.citus_cluster.get_sessions_log_table()

    # Receive the metrics computed by the monitor phase and compute the average metric of each VM.
    def analyze_with_average(self, vms_observations):
        vms_average = []
        vote_to_scale_out = 0
        vote_to_scale_in = 0
        vote_nothing = 0

        # For each VM compute the average metric of the past observations_interval observations
        for vm_name in vms_observations.keys():
            vm_average_metric = utils.list_average(vms_observations[vm_name], tuple_list=True)
            if(vm_average_metric > self.upper_threshold):
                vote_to_scale_out += 1
            elif(vm_average_metric < self.lower_threshold):
                vote_to_scale_in += 1
            else:
                vote_nothing += 1
            vms_average.append(vm_average_metric)
            self.performance_logger.info("METRIC;"+vm_name+";"+str(vm_average_metric))

        return vote_to_scale_out, vote_to_scale_in, vote_nothing, vms_average

    def analyze_with_duration(self, vms_observations):
        vms_average = []
        vote_to_scale_out = 0
        vote_to_scale_in = 0
        vote_nothing = 0

        # For each VM compute for how many minutes the VM's metric exceed the upper/lower threshold
        for vm_name in vms_observations.keys():
            vm_average_metric = utils.list_average(vms_observations[vm_name], tuple_list=True)
            violate_upper_threshold = utils.greater_than_threshold(vms_observations[vm_name], self.upper_threshold, tuple_list=True)
            violate_lower_threshold = utils.less_than_threshold(vms_observations[vm_name], self.lower_threshold, tuple_list=True)

            # If for all the previous observations the metric was > self.upper_threshold, vote to scale out
            if(all(element == 1 for element in violate_upper_threshold)):
                vote_to_scale_out += 1
            # If for all the previous observations the metric was < self.lower_threshold, vote to scale in
            elif (all(element == 1 for element in violate_lower_threshold)):
                vote_to_scale_in += 1
            else:
                vote_nothing += 1

            # Log the metrics for the past observations
            for timestamp, metric_value in vms_observations[vm_name]:
                self.performance_logger.info(str(timestamp)+";METRIC;"+vm_name+";"+str(metric_value))

            vms_average.append(vm_average_metric)

        return vote_to_scale_out, vote_to_scale_in, vote_nothing, vms_average

    def analyze_with_user_sessions(self, query_result):
        logging.info("analyzing with user session")

        vote_to_scale_out = 0
        vote_to_scale_in = 0
        vote_nothing = 0

        # If the database is running for sufficient amount of time
        if(query_result[0][1] is not None):
            # Compute the change rate of user sessions between the desired period
            sessions_difference_percentage = (query_result[1][1] - query_result[0][1]) / query_result[0][1]
            sessions_difference_percentage = sessions_difference_percentage * 100

            self.performance_logger.info(str(sessions_difference_percentage))
            self.performance_logger.info(str(query_result[1][1]))
            self.performance_logger.info(str(query_result[0][1]))
            if(sessions_difference_percentage > self.upper_threshold):
                vote_to_scale_out = 1
                vote_to_scale_in = 0
            elif(sessions_difference_percentage < -1 * self.upper_threshold):
                vote_to_scale_in = 1
                vote_to_scale_out = 0

            return vote_to_scale_out, vote_to_scale_in, vote_nothing, []
        else:
            return 0, 0, 0, []

    def plan_n_execute(self, vote_to_scale_out, vote_to_scale_in, vote_nothing, vms_average):
        logging.info("Plan n Execute")
        # Scale out according to votes
        if(vote_to_scale_out > vote_to_scale_in and vote_to_scale_out > vote_nothing):
            self.performance_logger.info("SCALEOUT;;1")
            self.k8s_cluster.cluster_scale_out(2, self.performance_logger)
            self.enter_cool_down_period(30)
        # Scale in according to votes
        elif(vote_to_scale_out < vote_to_scale_in and vote_to_scale_in > vote_nothing):
            self.performance_logger.info("SCALEIN;;1")
            self.k8s_cluster.cluster_scale_in(2, self.performance_logger)
            self.enter_cool_down_period(30)
        elif(not vms_average):
            self.performance_logger.info("DONOTHING;;1")
            return
        # If no decision can be taken according to votes, compute the global average metric
        else:
            global_average = utils.list_average(vms_average)
            if(global_average > self.upper_threshold):
                self.performance_logger.info("SCALEOUT;;1")
                self.k8s_cluster.cluster_scale_out(2, self.performance_logger)
                self.enter_cool_down_period(30)
            elif(global_average < self.lower_threshold):
                self.performance_logger.info("SCALEIN;;1")
                self.k8s_cluster.cluster_scale_in(2, self.performance_logger)
                self.enter_cool_down_period(30)


    def enter_cool_down_period(self, minutes):
        self.performance_logger.info("COOLDOWN;;"+str(minutes))
        # Sleep
        time.sleep(minutes * 60)

    def run(self):

        # Daemon restarted
        if (os.path.exists(self.storage_path)):
            logging.info("Continuing from a past state...")

        # Daemon initialized for the first time
        else:
            logging.info("Starting new state")
            os.mkdir(self.storage_path)
        # to be handled according to start/restart
        self.k8s_cluster = K8sCluster(self.minvm, self.maxvm)

        if (self.metric == "sessions"):
            logging.info("Autoscaling using user sessions...")
            # Run Daemon's job
            while True:
                vote_to_scale_out, vote_to_scale_in, vote_nothing, vms_average = self.analyze_with_user_sessions(
                    self.monitor_with_system_traffic())
                self.plan_n_execute(vote_to_scale_out, vote_to_scale_in, vote_nothing, vms_average)
                time.sleep(60)
        elif (self.metric == "cpu"):
            logging.info("Autoscaling using CPU...")
            # Run Daemon's job
            while True:
                vote_to_scale_out, vote_to_scale_in, vote_nothing, vms_average = self.analyze_with_duration(self.monitor_azure_metrics())
                self.plan_n_execute(vote_to_scale_out, vote_to_scale_in, vote_nothing, vms_average)
                time.sleep(60)

if __name__ == '__main__':

    # Parse the input arguments
    parser = argparse.ArgumentParser(description='Reading Auto-scaling arguments.')
    parser.add_argument('--action', dest='action', required=True, choices=['start', 'stop', 'restart'],
                        help='available auto-scaling daemon actions: {start, stop, restart}')
    parser.add_argument('--minvm', dest='minvm', required=True,
                        help='Minimum number of Worker VMs.')
    parser.add_argument('--maxvm', dest='maxvm', required=True,
                        help='Maximum number of Worker VMs.')
    parser.add_argument('--storage', dest='storage_path', required=True,
                        help='Specify a storage path.')
    parser.add_argument('--lower_th', dest='lower_threshold', required=True,
                        help='Specify the lower threshold for the metric.')
    parser.add_argument('--upper_th', dest='upper_threshold', required=True,
                        help='Specify the upper threshold for the metric.')
    parser.add_argument('--metric', dest='used_metric', required=True,
                        help='Specify the desired metric to be used. The available metrics are: sessions (A metric that monitors the users activity and adapt the size of the cluster to the number of users), cpu (A metric that uses the CPU percentage of the VMs)')
    args = parser.parse_args()

    # Check if range arguments are correct
    utils.range_type(args.used_metric, args.minvm, args.maxvm, 0)
    utils.range_type(args.used_metric, args.lower_threshold, args.upper_threshold, 0, 100)

    # Check if metric argument is correct
    utils.is_metric_valid(args.used_metric)

    performance_logger = utils.setup_loggers()

    # Get Daemon PID
    pidfile = os.path.join(os.getcwd(), "/var/run/autoscaling.pid")

    d = AutoscalingDaemon(pidfile, performance_logger, int(args.minvm), int(args.maxvm),
                          args.storage_path, int(args.lower_threshold), int(args.upper_threshold),
                          args.used_metric, observations_interval=3
                          )

    # Decide which Daemon action to do
    if args.action == "start":
        d.start()
    elif args.action == "stop":
        d.stop()
    elif args.action == "restart":
        d.restart()