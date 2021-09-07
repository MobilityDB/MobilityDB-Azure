import traceback
import os
from time import sleep
from datetime import datetime, timedelta

from azure.identity import ClientSecretCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.monitor import MonitorManagementClient
from msrestazure.azure_exceptions import CloudError



class Azure:
    def __init__(self):
        self.set_Azure_credentials()
        self.create_Azure_clients()
        self.resource_group = os.environ['RESOURCE_GROUP']
        self.monitor = self.Monitor(self, self.credentials, self.subscription_id, self.resource_group)

    # Set the Azure credential using the pre-generated Service Principal
    def set_Azure_credentials(self):
        self.subscription_id = os.environ['AZURE_SUBSCRIPTION_ID']
        self.credentials = ClientSecretCredential(
            client_id=os.environ['AZURE_CLIENT_ID'],
            client_secret=os.environ['AZURE_CLIENT_SECRET'],
            tenant_id=os.environ['AZURE_TENANT_ID']
        )

    # Create all clients with an Application (service principal) token provider
    def create_Azure_clients(self):
        self.resource_client = ResourceManagementClient(self.credentials, self.subscription_id)
        self.compute_client = ComputeManagementClient(self.credentials, self.subscription_id)
        self.network_client = NetworkManagementClient(self.credentials, self.subscription_id)

    # Return a list with the deployed Virtual Machines under self.resource_group Resource Group
    def get_deployed_vms(self):
        return self.compute_client.virtual_machines.list(self.resource_group)

    def delete_vms(self, vms_numbers):
        for vm_number in vms_numbers:
            vm_name = "Worker"+str(vm_number)
            nic_name = vm_name+"VMNic"
            nsg_name = vm_name+"NSG"
            ip_name = vm_name+"PublicIP"

            # Delete VM
            print('Delete VM {}'.format(vm_name))
            print('Delete NIC {}'.format(nic_name))
            try:
                async_vm_delete = self.compute_client.virtual_machines.begin_delete(self.resource_group, vm_name)
                async_vm_delete.wait()
                net_del_poller = self.network_client.network_interfaces.begin_delete(self.resource_group, nic_name)
                net_del_poller.wait()
                # Wait until the Network Interface is deleted to proceed

                while(not net_del_poller.done()):
                    sleep(5)

                async_nsg = self.network_client.network_security_groups.begin_delete(self.resource_group, nsg_name)
                async_nsg.wait()
                async_ip = self.network_client.public_ip_addresses.begin_delete(self.resource_group, ip_name)
                async_ip.wait()
                disks_list = self.compute_client.disks.list_by_resource_group(self.resource_group)
                disk_handle_list = []
                
                # Delete the attached disks
                for disk in disks_list:
                    if vm_name in disk.name:
                        print('Delete Disk {}'.format(disk.name))
                        async_disk_delete = self.compute_client.disks.begin_delete(self.resource_group, disk.name)
                        disk_handle_list.append(async_disk_delete)
                print("Queued disks will be deleted now...")
                for async_disk_delete in disk_handle_list:
                    async_disk_delete.wait()
            except CloudError:
                print('A VM delete operation failed: {}'.format(traceback.format_exc()))
            print("Deleted VM {}".format(vm_name))

    # Return Coordinator's VM public ip address
    def get_coordinator_ip(self):
        ip_addresses = self.network_client.public_ip_addresses.list(self.resource_group)
        for ip in ip_addresses:
            if (ip.name == "CoordinatorPublicIP"):
                return ip.ip_address

    # Return worker_name's public ip address
    def get_worker_ip(self, worker_name):
        ip_addresses = self.network_client.public_ip_addresses.list(self.resource_group)
        for ip in ip_addresses:
            if (ip.name == worker_name + "PublicIP"):
                return ip.ip_address

    class Monitor:
        def __init__(self, parent, credentials, subscription_id, resource_group):
            print("Created Monitor Instance")
            self.parent = parent
            self.resource_group = resource_group
            self.subscription_id = subscription_id
            self.monitor_client = MonitorManagementClient(
                credentials,
                subscription_id
            )

        # Return a list of values for each VM under the given Resource Group.. Each list represents the timeseries of the specified metric for the VM.
        # The timeseries contains the values of the last "internval" minutes and the granulatiry is of 1 minute.
        # Aggregation parameter spesifies how the returned metrics are aggregated: {Average, Total, Minimum, Maximum, Count}
        def get_azure_metric(self, metric, interval, aggregation='Average'):
            # Get the VMs' names
            vm_list = self.parent.get_deployed_vms()
            result = {}

            # For each VM, request the desired metric
            for vm in vm_list:
                vm_name = vm.name
                # Ignore Coordinator's metrics
                if(vm_name == "Coordinator"):
                    continue

                # Create VM's resource id
                resource_id = (
                    "subscriptions/{}/"
                    "resourceGroups/{}/"
                    "providers/Microsoft.Compute/virtualMachines/{}"
                ).format(self.subscription_id, self.resource_group, vm_name)

                now = datetime.utcnow()
                start_time = now - timedelta(minutes=interval+1)

                metrics_data = self.monitor_client.metrics.list(
                    resource_id,
                    timespan="{}/{}".format(start_time, now),
                    interval='PT1M',
                    metricnames=metric,
                    aggregation=aggregation
                )

                timeserie_res = []
                for item in metrics_data.value:
                    for timeserie in item.timeseries:
                        for data in timeserie.data:
                            # azure.mgmt.monitor.models.MetricData
                            if(aggregation == "Average"):
                                timeserie_res.append((data.time_stamp, data.average))
                            elif (aggregation == "Total"):
                                timeserie_res.append((data.time_stamp, data.total))
                            elif (aggregation == "Minimum"):
                                timeserie_res.append((data.time_stamp, data.minimum))
                            elif (aggregation == "Maximum"):
                                timeserie_res.append((data.time_stamp, data.maximum))
                            elif (aggregation == "Count"):
                                timeserie_res.append((data.time_stamp, data.count))

                # Add the timeseries of the VM in a dictionary
                result[vm_name] = timeserie_res
            return result

