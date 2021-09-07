#!/bin/bash

#Shell commands to be run on K8S master node.
#Cluster initialization 2. 
HOME=/home/azureuser
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
sudo kubectl apply -f "https://cloud.weave.works/k8s/net?k8s-version=$(kubectl version | base64 | tr -d '\n')"
sudo kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/v2.2.0/aio/deploy/recommended.yaml

#By default, the cluster will not schedule pods on the control-plane node for security reasons. 
#If you want to be able to schedule pods on the control-plane node, run:
sudo kubectl label nodes coordinator dedicated=master
sudo kubectl taint nodes --all node-role.kubernetes.io/master-