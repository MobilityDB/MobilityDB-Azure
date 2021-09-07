#!/bin/bash
sudo apt-get update
yes | sudo apt-get install \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg-agent \
    software-properties-common

curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -

sudo add-apt-repository \
   "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
   $(lsb_release -cs) \
   stable"

sudo apt-get update
yes | sudo apt-get install docker-ce="5:18.09.0~3-0~ubuntu-bionic" docker-ce-cli="5:18.09.0~3-0~ubuntu-bionic" containerd.io

sudo echo "{\"exec-opts\": [\"native.cgroupdriver=systemd\"]}" > /home/azureuser/daemon.json
sudo mv /home/azureuser/daemon.json /etc/docker/daemon.json
sudo systemctl restart docker

# Start downloading the image in the background to gain time later
sudo docker pull dimitris007/mobilitydb:citus10 &

# Install Kubernetes
sudo apt install selinux-utils
setenforce 0
#sed -i --follow-symlinks 's/SELINUX=enforcing/SELINUX=disabled/g' /etc/sysconfig/selinux
swapoff -a

sudo apt-get update && sudo apt-get install -y apt-transport-https curl
curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
cat <<EOF | sudo tee /etc/apt/sources.list.d/kubernetes.list
deb https://apt.kubernetes.io/ kubernetes-xenial main
EOF
sudo apt-get update
sudo apt-get install -y kubelet kubeadm kubectl
sudo apt-mark hold kubelet kubeadm kubectl