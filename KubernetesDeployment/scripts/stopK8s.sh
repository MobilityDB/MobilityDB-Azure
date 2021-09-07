#!/bin/bash
sudo kubectl patch pvc postgres-pv-claim -p '{"metadata":{"finalizers": []}}' --type=merge
sudo kubectl patch pv postgres-pv-volume-coordinator -p '{"metadata":{"finalizers": []}}' --type=merge

sudo kubectl delete service citus-master 
sudo kubectl delete service citus-workers
sudo kubectl delete deployment citus-master
sudo kubectl delete statefulset citus-worker
sudo kubectl delete persistentvolumeclaim postgres-pv-claim
sudo kubectl delete persistentvolume postgres-pv-volume
sudo kubectl delete persistentvolumeclaim postgres-pv-claim-coordinator
sudo kubectl delete persistentvolume postgres-pv-volume-coordinator
sudo kubectl delete secret postgresql-secrets
sudo kubectl delete secret postgres-secrets-params
