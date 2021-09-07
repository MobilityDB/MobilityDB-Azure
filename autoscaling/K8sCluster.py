"""Create and manage virtual machines.
This script expects that the following environment vars are set:
AZURE_TENANT_ID: your Azure Active Directory tenant id or domain
AZURE_CLIENT_ID: your Azure Active Directory Application Client ID
AZURE_CLIENT_SECRET: your Azure Active Directory Application Secret
AZURE_SUBSCRIPTION_ID: your Azure Subscription Id
"""
import subprocess
import os
import CitusCluster
import Azure
from kubernetes import client, config
import time

class K8sCluster:

    def __init__(self, minimum_vms, maximum_vm):
        # Configs can be set in Configuration class directly or using helper utility
        config.load_kube_config()
        self.k8s = client.CoreV1Api()

        self.AZUREPASSWORD = os.environ['AZURE_CLIENT_SECRET']
        self.SCRIPTPATH = os.environ['SCRIPTPATH']
        self.minimum_vms = minimum_vms
        self.maximum_vm = maximum_vm

        self.azure = Azure.Azure()
        self.COORDIP = self.azure.get_coordinator_ip()
        self.citus_cluster = CitusCluster.CitusCluster(self.COORDIP)


    # Add vm_to_create number of VMs to the existing Kubernetes cluster
    def cluster_scale_out(self, vm_to_create, performance_logger):
        vm_list = self.azure.get_deployed_vms()
        max_worker_name = 0
        vm_name_list = []

        # Get the current number of Worker nodes
        for vm in vm_list:
            if(vm.name != "Coordinator"):
                if(len(vm.name.split("Worker")) == 2 and vm.name.split("Worker")[1].isnumeric() and int(vm.name.split("Worker")[1]) > max_worker_name):
                    max_worker_name = int(vm.name.split("Worker")[1])
                    vm_name_list.append(int(vm.name.split("Worker")[1]))

        # Decide whether more VMs can be added
        if (len(vm_name_list) + vm_to_create <= self.maximum_vm):
            print("creating "+str(vm_to_create) + "VMs")
            # Call the addNewVms.sh bash script to deploy vm_to_create number of VMs
            rc = subprocess.check_call([self.SCRIPTPATH+'/addNewVms.sh', self.AZUREPASSWORD, str(max_worker_name + 1), str(max_worker_name + vm_to_create), str(max_worker_name + vm_to_create - 1)])
            # Wait until the StatefulSet has scaled (30 seconds for each new machine)
            time.sleep(30 * vm_to_create)
            # Rebalance table shards
            performance_logger.info("REBALANCING;;")
            self.citus_cluster.rebalance_table_shards()
        # If the maximum number of VMs will be exceeded, modify the number of VMs to be added
        else:
            vm_to_create = self.maximum_vm - len(vm_name_list)
            if (vm_to_create > 0):
                print("creating " + str(vm_to_create) + "VMs")
                # Call the addNewVms.sh bash script to deploy vm_to_create number of VMs
                rc = subprocess.check_call([self.SCRIPTPATH+'/addNewVms.sh', self.AZUREPASSWORD, str(max_worker_name + 1), str(max_worker_name + vm_to_create), str(max_worker_name + vm_to_create -1)])
                # Wait until the StatefulSet has scaled (30 seconds for each new machine)
                time.sleep(30 * vm_to_create)
                # Rebalance table shards
                performance_logger.info("REBALANCING;;")
                self.citus_cluster.rebalance_table_shards()


    def cluster_scale_in(self, vm_to_delete, performance_logger):
        vm_list = self.azure.compute_client.virtual_machines.list("ClusterGroup")
        vm_name_list = []
        remove_flag = False

        # Append all the Worker names in a list
        for vm in vm_list:
            if (vm.name != "Coordinator"):
                if (len(vm.name.split("Worker")) == 2 and vm.name.split("Worker")[1].isnumeric()):
                    vm_name_list.append(int(vm.name.split("Worker")[1]))

        # Decide whether there are enough VMs to remove
        if(len(vm_name_list) - vm_to_delete >= self.minimum_vms):
            remove_flag = True
        # If there are not enough VMs to delete, delete vm_to_delete VMs to reach the minimum accepted
        # number of VMs (self.minimum_vms)
        else:
            vm_to_delete = len(vm_name_list) - self.minimum_vms
            if(vm_to_delete > 0):
                remove_flag = True

        if(remove_flag):
            # Sort the list in descending order
            vm_name_list.sort(reverse=True)
            workers_ip = []
            for i in range(vm_to_delete):
                # Get pod's ip
                workers_ip.append(self.get_pod_internal_ip(vm_name_list[i]-1))
            # Delete Worker nodes from Citus cluster
            performance_logger.info("CITUS_CLUSTER_SCALEIN;;")
            self.citus_cluster.delete_node(workers_ip)
            # Delete Worker nodes from K8s cluster
            performance_logger.info("K8S_SCALEIN;;")
            new_cluster_size = len(vm_name_list) - vm_to_delete
            self.delete_cluster_nodes(new_cluster_size, vm_name_list[:vm_to_delete])
            # Delete Worker nodes from Azure
            performance_logger.info("AZURE_SCALEIN;;")
            self.azure.delete_vms(vm_name_list[:vm_to_delete])

    # Return the ip of the pod with name citus-worker-[worker_num]
    def get_pod_internal_ip(self, worker_num):
        ret = self.k8s.list_pod_for_all_namespaces(watch=False)
        for pod in ret.items:
            if(pod.metadata.name == "citus-worker-"+str(worker_num)):
                return pod.status.pod_ip

    # Delete K8s cluster nodes
    def delete_cluster_nodes(self, new_cluster_size, worker_numbers):
        # Scale in the Stateful Set
        subprocess.check_call(['sudo', 'kubectl', 'scale', 'statefulsets', 'citus-worker', '--replicas=%s' % str(new_cluster_size)] )
        # Wait 10 seconds until the pod is terminated
        time.sleep(10)
        for worker_num in worker_numbers:
            worker_name = "worker"+str(worker_num)
            print(worker_name)
            # Drain the node
            subprocess.check_call(['sudo', 'kubectl', 'drain', worker_name, '--ignore-daemonsets'])
            # Delete the node
            subprocess.check_call(['sudo', 'kubectl', 'delete', 'node', worker_name])
