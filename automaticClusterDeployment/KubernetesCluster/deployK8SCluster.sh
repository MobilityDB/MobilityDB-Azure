#!/bin/bash
################################################################################
#							 Script Description						   		   #
################################################################################
# This script is used to automatically deploy a MobilityDB cluster on the Cloud.
# More specifically, the cluster will be hosted in Microsoft Azure, hence an Azure
# account with a valid subscription is needed to run it. To corectly initialize the 
# cluster, the following Configuration tab should be parametrized:
# AzureUsername parameter is used to login your Azure account.
# The default ResourceGroupName, Location and VirtualNetwork values can be used.
# Subscription defines the name of the active Azure subscription.
# VMsNumber determines the number of Worker nodes and VMsSize the size of each machine. 
# SSHPublicKeyPath and SSHPrivateKeyPath values specify the location of the ssh private 
# and public keys to access the created VMs. By default, the files will be stored in 
# ~/.ssh/ directory. Finally, Gitrepo specifies the Github repository from which the
# installation scripts and the rest source files will be found.

################################################################################
#							    Configuration						   		   #
################################################################################
AzureUsername="zas1122@hotmail.com"
ResourceGroupName="TestGroup"
Location="germanywestcentral"
VirtualNetwork="test-vnet"
Subscription="CODE WIT"
VMsNumber=1
VMsSize="Standard_B2s" #Visit https://azure.microsoft.com/en-us/pricing/details/virtual-machines/series/ 
# to see the full list of available VMs
SSHPublicKeyPath="~/.ssh/id_rsa.pub"
SSHPrivateKeyPath="~/.ssh/id_rsa"
Gitrepo="https://github.com/JimTsesm/MobilityDB-Azure.git"
Service_app_url="http://python-app2"
Service_tenant="18f19e28-1ea1-4b0c-bbc0-cf7538f92d05"
################################################################################


#Login to Azure using Azure CLI
#read -sp "Azure password: " AZ_PASS && echo && az login -u $AzureUsername -p $AZ_PASS
read -sp "Azure Client secret: " AZ_PASS && echo && az login --service-principal -u "$Service_app_url" -p $AZ_PASS --tenant "$Service_tenant"

#Select the desired subscription
az account set --subscription "$Subscription"

#Create a new Resource Group
az group create --name $ResourceGroupName --location $Location

#Create a new Virtual Network
az network vnet create --name $VirtualNetwork --resource-group $ResourceGroupName --subnet-name default

################################################################################
#							    Coordinator Creation						   #
################################################################################

VMName="Coordinator";

#Create a VM for the coordinator
az vm create --name $VMName --resource-group $ResourceGroupName --public-ip-address-allocation static --image "UbuntuLTS" --size $VMsSize --vnet-name $VirtualNetwork --subnet default --admin-username azureuser --generate-ssh-keys;

#Open port 6443 to allow K8S connections
az vm open-port -g $ResourceGroupName -n $VMName --port 6443 --priority 1020;

#Open port 30001 to allow K8S service exposure
az vm open-port -g $ResourceGroupName -n $VMName --port 30001 --priority 1030;


#Clone the github repository to the VM
az vm run-command invoke -g $ResourceGroupName -n $VMName --command-id RunShellScript --scripts "git clone $Gitrepo /home/azureuser/MobilityDB-Azure"

#Execute the installtion scripts from the clone GitHub repository	 	
az vm run-command invoke -g $ResourceGroupName -n $VMName --command-id RunShellScript --scripts "sudo bash /home/azureuser/MobilityDB-Azure/automaticClusterDeployment/KubernetesCluster/installDockerK8s.sh"
az vm run-command invoke -g $ResourceGroupName -n $VMName --command-id RunShellScript --scripts "sudo bash /home/azureuser/MobilityDB-Azure/automaticClusterDeployment/KubernetesCluster/runOnMaster.sh"
az vm run-command invoke -g $ResourceGroupName -n $VMName --command-id RunShellScript --scripts "sudo bash /home/azureuser/MobilityDB-Azure/automaticClusterDeployment/KubernetesCluster/runOnMaster2.sh"

#Get Join token from the logs of the previous command (sudo kubeadm init)
#Operations: cat the log, remove \n and \, get everything after "kubeadm join" until the next \ and finally remove the \
JOINCOMMAND=$(az vm run-command invoke -g $ResourceGroupName -n Coordinator --command-id RunShellScript --scripts "sudo cat /var/lib/waagent/run-command/download/2/stdout" | sed 's/\\n/ /g' | sed 's/\\\\/ /g' |grep -o 'kubeadm join.*   \[' | sed 's/\[//g' | sed 's/\\t/ /g')

echo "Coordinator Node was successfully deployed."
################################################################################


################################################################################
#								Workers Creation							   #
################################################################################

#Create the VMs with the given parameters
for i in $(seq 1 $VMsNumber)
do
	VMName="Worker$i";

	#Create the VM
	az vm create	--name $VMName --resource-group $ResourceGroupName --public-ip-address-allocation static --image "UbuntuLTS" --size $VMsSize --vnet-name $VirtualNetwork --subnet default --ssh-key-value $SSHPublicKeyPath --admin-username azureuser &

done
wait #for all the subprocesses of the parallel loop to terminate

for i in $(seq 1 $VMsNumber)
do
	VMName="Worker$i";

	#Open port 5432 to accept inbound connection from the Citus coordinator
	az vm open-port -g $ResourceGroupName -n $VMName --port 5432 --priority 1010 &

done
wait #for all the subprocesses of the parallel loop to terminate

for i in $(seq 1 $VMsNumber)
do
	VMName="Worker$i";

	#Clone the github repository to the VM
	az vm run-command invoke -g $ResourceGroupName -n $VMName --command-id RunShellScript --scripts "git clone $Gitrepo /home/azureuser/MobilityDB-Azure" &

done
wait #for all the subprocesses of the parallel loop to terminate
	
#Install the required software to every Worker
#The for loop is executed in parallel. This means that every Worker will install the software at the same time.
for i in $(seq 1 $VMsNumber)
do
	VMName="Worker$i";
	
	#Execute the installtion script from the clone GitHub repository	 	
	az vm run-command invoke -g $ResourceGroupName -n $VMName --command-id RunShellScript --scripts "sudo bash /home/azureuser/MobilityDB-Azure/automaticClusterDeployment/KubernetesCluster/installDockerK8s.sh" &
done
wait #for all the subprocesses of the parallel loop to terminate

#Run the initialization commands in each Worker
for i in $(seq 1 $VMsNumber)
do
	VMName="Worker$i";
	
	#Execute the installtion script from the clone GitHub repository	 	
	az vm run-command invoke -g $ResourceGroupName -n $VMName --command-id RunShellScript --scripts "sudo bash /home/azureuser/MobilityDB-Azure/automaticClusterDeployment/KubernetesCluster/runOnWorker.sh" &
done
wait #for all the subprocesses of the parallel loop to terminate

echo "Worker Nodes were successfully deployed."


#Add each Worker Node to K8S Cluster
for i in $(seq 1 $VMsNumber)
do
	VMName="Worker$i";
	az vm run-command invoke -g $ResourceGroupName -n $VMName --command-id RunShellScript --scripts "$JOINCOMMAND"
done

echo "Worker Nodes were successfully added to the cluster."
################################################################################


################################################################################
#								MobilityDB Deployment						   #
################################################################################

#az vm run-command invoke -g $ResourceGroupName -n Coordinator --command-id RunShellScript --scripts "bash /home/azureuser/MobilityDB-Azure/KubernetesDeployment/scripts/startK8s.sh"

################################################################################
