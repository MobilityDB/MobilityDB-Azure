#!/bin/bash
################################################################################
#							    Configuration						   		   #
################################################################################
AzureUsername="zas1122@hotmail.com"
ResourceGroupName="TestGroup"
Location="germanywestcentral"
VirtualNetwork="test-vnet"
Subscription="CODE WIT"
VMsSize="Standard_B2s" #Visit https://azure.microsoft.com/en-us/pricing/details/virtual-machines/series/ 
# to see the full list of available VMs
SSHPublicKeyPath="~/.ssh/id_rsa.pub"
SSHPrivateKeyPath="~/.ssh/id_rsa"
Gitrepo="https://github.com/JimTsesm/MobilityDB-Azure.git"
Service_app_url="http://python-app2"
Service_tenant="18f19e28-1ea1-4b0c-bbc0-cf7538f92d05"
################################################################################

#Login to Azure using Azure CLI and Serice Principal credentials
#az login -u $AzureUsername -p $1
az login --service-principal -u "$Service_app_url" -p $1 --tenant "$Service_tenant"

#Select the desired subscription
az account set --subscription "$Subscription"


################################################################################
#								Workers Creation							   #
################################################################################

#Create the VMs with the given parameters in parallel
for i in $(seq $2 $3)
do
	VMName="Worker$i";
	
	#Create the VM
	az vm create	--name $VMName --resource-group $ResourceGroupName --public-ip-address-allocation static --image "UbuntuLTS" --size $VMsSize --vnet-name $VirtualNetwork --subnet default --ssh-key-value $SSHPublicKeyPath --admin-username azureuser &
done
wait #for all the subprocesses of the parallel loop to terminate

for i in $(seq $2 $3)
do
	VMName="Worker$i";

	#Open port 5432 to accept inbound connection from the Citus coordinator
	az vm open-port -g $ResourceGroupName -n $VMName --port 5432 --priority 1010;

	#Clone the github repository to the VM
	az vm run-command invoke -g $ResourceGroupName -n $VMName --command-id RunShellScript --scripts "git clone $Gitrepo /home/azureuser/MobilityDB-Azure" &
done
wait #for all the subprocesses of the parallel loop to terminate

#Install the required software to every Worker
#The for loop is executed in parallel. This means that every Worker will install the software at the same time.
for i in $(seq $2 $3)
do
	VMName="Worker$i";

	#Execute the installation script 	
	az vm run-command invoke -g $ResourceGroupName -n $VMName --command-id RunShellScript --scripts "sudo bash /home/azureuser/MobilityDB-Azure/automaticClusterDeployment/KubernetesCluster/installDockerK8s.sh" &
done
wait #for all the subprocesses of the parallel loop to terminate

#Run the initialization commands to each Worker
for i in $(seq $2 $3)
do
	VMName="Worker$i";
	
	#Execute the runOnWorker.sh file to take the required actions to the Worker node	 	
	az vm run-command invoke -g $ResourceGroupName -n $VMName --command-id RunShellScript --scripts "sudo bash /home/azureuser/MobilityDB-Azure/automaticClusterDeployment/KubernetesCluster/runOnWorker.sh" &
done
wait #for all the subprocesses of the parallel loop to terminate

echo "Worker Nodes were successfully deployed."

#Generate a new join token
VMName="Coordinator"
JOINCOMMAND=$(az vm run-command invoke -g $ResourceGroupName -n $VMName --command-id RunShellScript --script "sudo kubeadm token create --print-join-command" | sed 's/\\n/ /g' | sed 's/\\\\/ /g' |grep -o 'kubeadm join.*   \[' | sed 's/\[//g')

#Add each Worker Node to K8S Cluster
for i in $(seq $2 $3)
do
	VMName="Worker$i";
	az vm run-command invoke -g $ResourceGroupName -n $VMName --command-id RunShellScript --scripts "$JOINCOMMAND"
done

echo "Worker Nodes were successfully added to the cluster."

#Scale out the stateful set
kubectl scale statefulsets citus-worker --replicas=$3
