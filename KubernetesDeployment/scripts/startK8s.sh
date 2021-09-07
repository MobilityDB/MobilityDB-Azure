#!/bin/bash
PATHTOFILES="/home/azureuser/MobilityDB-Azure//KubernetesDeployment"
sudo kubectl create secret generic postgresql-secrets --from-file=$PATHTOFILES/secrets/
sudo kubectl create -f $PATHTOFILES/postgres-secrets-params.yaml
sudo kubectl create -f $PATHTOFILES/postgres-storage-worker.yaml
sudo kubectl create -f $PATHTOFILES/postgres-storage-coordinator.yaml  
sudo kubectl create -f $PATHTOFILES/postgres-deployment.yaml 
sudo kubectl create -f $PATHTOFILES/postgres-service.yaml
sudo kubectl create -f $PATHTOFILES/postgres-deployment-workers.yaml
sudo kubectl create -f $PATHTOFILES/postgres-service-workers.yaml
