#!/bin/bash
sudo chmod 777 /etc/systemd/system/kubelet.service.d/10-kubeadm.conf
sudo sed '${s/$/ --cgroup-driver=systemd/}' /etc/systemd/system/kubelet.service.d/10-kubeadm.conf > 10-kubeadm.conf
sudo rm /etc/systemd/system/kubelet.service.d/10-kubeadm.conf
sudo mv ./10-kubeadm.conf /etc/systemd/system/kubelet.service.d/10-kubeadm.conf
sudo chmod 640 /etc/systemd/system/kubelet.service.d/10-kubeadm.conf

yes | sudo apt-get install firewalld
sudo systemctl daemon-reload
sudo systemctl restart kubelet
sudo systemctl status kubelet

#Disable firewall when worker cannot connect to master
sudo iptables --flush
sudo iptables -tnat --flush
sudo systemctl stop firewalld
sudo systemctl disable firewalld
sudo systemctl restart docker