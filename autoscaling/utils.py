import argparse
import logging


def range_type(metric, min, max, min_required, max_required=None):
    if(metric not in ["cpu"]):
        return
    try:
        min = int(min)
        max = int(max)
    except ValueError as err:
        print(f'You entered , which is not a positive number.')
        raise argparse.ArgumentTypeError("minvm and maxvm should be positive integers")

    if(max_required is None):
        if (min > min_required and max > min):
            return
        else:
            raise argparse.ArgumentTypeError("minvm shoulb be < than maxvm.")
    else:
        if (min > min_required and max < max_required and max > min):
            return
        else:
            raise argparse.ArgumentTypeError("minvm shoulb be < than maxvm.")

def is_metric_valid(used_metric):
    if used_metric not in ["cpu", "sessions"]:
        raise argparse.ArgumentTypeError("the used_metric flag receives one of the following arguments: cpu, sessions")

def list_average(integers_list, tuple_list=False):
    if(tuple_list):
        if(len(integers_list) > 0):
            l = [pair[1] for pair in integers_list if (pair[1] is not None and pair[1] > 0.0)]
            return sum(l) / len(l)
        else:
            return 0.0
    else:
        if (len(integers_list) > 0):
            l = [i for i in integers_list if (i is not None and i > 0.0)]
            return sum(l) / len(l)
        else:
            return 0.0

def greater_than_threshold(observation_list, u_threshold, tuple_list=False):
    if (tuple_list):
        return [1 if (pair[1] is None or pair[1] > u_threshold) else 0 for pair in observation_list]

def less_than_threshold(observation_list, l_threshold, tuple_list=False):
    if (tuple_list):
        return [1 if (pair[1] is None or pair[1] < l_threshold) else 0 for pair in observation_list]

def setup_loggers(level=logging.INFO):
    # Configure the default logger
    logging.basicConfig(filename='/var/log/autoscaling.log', level=logging.INFO, filemode='a',
                        format='[%(asctime)s] - %(levelname)s - %(message)s')
    # Configure the performance logger
    formatter = logging.Formatter('[%(asctime)s];%(levelname)s;%(message)s')
    handler = logging.FileHandler("/var/log/autoscaling_performance.log", mode='a')
    handler.setFormatter(formatter)

    performance_logger = logging.getLogger("performance_logger")
    performance_logger.setLevel(level)
    performance_logger.addHandler(handler)

    return performance_logger
