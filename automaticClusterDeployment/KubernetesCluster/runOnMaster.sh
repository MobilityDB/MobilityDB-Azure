#!/bin/bash

#Shell commands to be run on K8S master node.

# Install pip
yes | sudo apt install python3-pip
yes | sudo apt install virtualenv
yes | apt-get install python3-venv

yes | sudo apt-get install libssl-dev

#Install Azure CLI
yes | sudo apt-get update
yes | sudo apt-get install ca-certificates curl apt-transport-https lsb-release gnupg
curl -sL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/microsoft.gpg > /dev/null
AZ_REPO=$(lsb_release -cs)
echo "deb [arch=amd64] https://packages.microsoft.com/repos/azure-cli/ $AZ_REPO main" |
    sudo tee /etc/apt/sources.list.d/azure-cli.list
yes | sudo apt-get update
yes | sudo apt-get install azure-cli

#Cluster initialization. 
sudo kubeadm init