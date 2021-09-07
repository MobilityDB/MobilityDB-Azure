#!/bin/bash
################################################################################
#							 Script Description						   		   #
################################################################################
# This script is used to automatically deploy a MobilityDB cluster on the Cloud.
# More specifically, the cluster will be hosted in Microsoft Azure, hence an Azure
# account with a valid subscription is needed to run it. To corectly initialize the 
# cluster, the following Configuration tab should be parametrized:
# The default ResourceGroupName, Location and VirtualNetwork values can be used. 
# VMsNumber determines the number of Worker nodes and VMsSize the size of each machine. 
# SSHPublicKeyPath and SSHPrivateKeyPath values specify the location of the ssh private 
# and public keys to access the created VMs. By default, the files will be stored in 
# ~/.ssh/ directory. Finally, InstallationScript specifies the path where the installMobilityDB.sh
# script is stored.

################################################################################
#							    Configuration						   		   #
################################################################################
ResourceGroupName="clustergroup"
Location="francecentral"
VirtualNetwork="clustergroup-vnet"
VMsNumber=3
VMsSize="Standard_B1ls" #Visit https://azure.microsoft.com/en-us/pricing/details/virtual-machines/series/ 
# to see the full list of available VMs
SSHPublicKeyPath="~/.ssh/id_rsa.pub"
SSHPrivateKeyPath="~/.ssh/id_rsa"
InstallationScript="/home/dimitris/Desktop/thesis/MobilityDB-Azure/automaticClusterDeployment/installMobilityDB.sh"
################################################################################


#Login to Azure using Azure CLI
az login

#Create a new Resource Group
az group create --name $ResourceGroupName --location $Location

#Create a new Virtual Network
az network vnet create --name $VirtualNetwork --resource-group $ResourceGroupName --subnet-name default


################################################################################
#							    Coordinator Creation						   #
################################################################################

VMName="Coordinator";

# #Create a VM for the coordinator
az vm create	--name $VMName --resource-group $ResourceGroupName --public-ip-address-allocation static --image "UbuntuLTS" --size $VMsSize --vnet-name $VirtualNetwork --subnet default --admin-username azureuser --generate-ssh-keys;

#Get VM's Public IP
ip=`az vm show -d -g $ResourceGroupName -n $VMName --query publicIps -o tsv`

#Send the bashscripts containing the commands to install the required software to the VM
scp -o StrictHostKeyChecking=no -i $SSHPrivateKeyPath $InstallationScript azureuser@$ip:/home/azureuser/installMobilityDB.sh;

#Execute the previously sent bash file	 	
az vm run-command invoke -g $ResourceGroupName -n $VMName --command-id RunShellScript --scripts "sudo bash /home/azureuser/installMobilityDB.sh"

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
	az vm create	--name $VMName --resource-group $ResourceGroupName --public-ip-address-allocation static --image "UbuntuLTS" --size $VMsSize --vnet-name $VirtualNetwork --subnet default --ssh-key-value $SSHPublicKeyPath --admin-username azureuser;

	#Open port 5432 to accept inbound connection from the Citus coordinator
	az vm open-port -g $ResourceGroupName -n $VMName --port 5432 --priority 1010;

	#Get VM's Public IP
	ip=`az vm show -d -g $ResourceGroupName -n $VMName --query publicIps -o tsv`

	#Send the bashscripts containing the commands to install the required software to the VM
	scp -o StrictHostKeyChecking=no -i $SSHPrivateKeyPath $InstallationScript azureuser@$ip:/home/azureuser/installMobilityDB.sh;
	
done

#Install the required software to every Worker
#The for loop is executed in parallel. This means that every Worker will install the software at the same time.
for i in $(seq 1 $VMsNumber)
do
	VMName="Worker$i";
	
	#Execute the previously sent bash file	 	
	az vm run-command invoke -g $ResourceGroupName -n $VMName --command-id RunShellScript --scripts "sudo bash /home/azureuser/installMobilityDB.sh" &
done
wait #for all the subprocesses of the parallel loop to terminate

echo "Worker Nodes were successfully deployed."


#Add each Worker Node to Citus Cluster
for i in $(seq 1 $VMsNumber)
do
	VMName="Worker$i";
	#Get VM's Public IP
	ip=`az vm show -d -g $ResourceGroupName -n $VMName --query publicIps -o tsv`

	az vm run-command invoke -g $ResourceGroupName -n Coordinator --command-id RunShellScript --scripts "sudo -i -u postgres psql -c \"SELECT * from master_add_node('$ip', 5432);\""
done

echo "Worker Nodes were successfully added to the cluster."
################################################################################
