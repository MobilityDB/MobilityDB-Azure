# Self-scalable Moving Object Databases on the Cloud: MobilityDB and Azure

**Author: Dimitrios Tsesmelis** <br>
**Email: tsesmelis.jim007@gmail.com** <br>
**Phone: (+30) 6949550129** 

This work has been performed during the 4rth semester of my MSc in Big Data Management and Analytics and it consists the product of my master's thesis. This repository is a copy of the original one that can be found [here](https://github.com/JimTsesm/MobilityDB-Azure). <br> 
A [detailed report](https://docs.mobilitydb.com/pub/MobilityDB-Azure.pdf) of the thesis is available as well as the [presentation slides](https://docs.mobilitydb.com/pub/MobilityDB-Azure_presentation.pdf) of the master's thesis defense.

## Abstract
PostgreSQL is one of the most promising and quickly evolving relational
database management systems. Being a fully extensible system, there are plenty of
projects that build functionalities on top of PostgreSQL. MobilityDB is such a tool
that enables users to efficiently store, manage and query moving object data, such
as data produced by fleets of vehicles. <br><br>
Living in the era of big data technologies and cloud computing, it is vital for
cutting-edge database management systems to provide cloud native solutions that
allow data processing at scale. Citus is such a tool that transforms any PostgreSQL
server into a distributed database, without preventing any PostgreSQL native functionality.<br><br>
Deploying a MobilityDB cluster using Citus on the cloud is rather a simple
task. It requires deep knowledge of handling the provided infrastructure, configuring
the network between the machines as well as time and effort to learn and
manage the peculiarities of each cloud provider. In addition, maintaining a scalable
system requires continuous monitoring of several factors and metrics that depict
the performance of the system. Such a task implies repeating human effort that is
sometime prone to errors.<br><br>
In this work, we aim to target the aforementioned challenges by introducing
automation to the rolling out process of a MobilityDB cluster on Microsoft Azure
as well as to partially automate the management and maintenance of the deployed
solution. Moreover, we provide a tool, called autoscaler, that is capable of automatically
monitoring the database cluster, analyzing the collected performance metrics
and making decisions that adapt the size of the cluster, according to the measured
workload.<br><br>
To assess the performance of our solution, we perform several experiments that
combine two different benchmarks, namely [BerlinMOD](https://github.com/MobilityDB/MobilityDB-BerlinMOD) and [Scalar](https://distrinet.cs.kuleuven.be/software/scalar/) benchmarks.
The first provides a synthetic dataset that simulates the behavior of moving vehicles
across Berlin, while the second one is used to simulate a number of concurrent
user requests that query the system under test.

## Automated Cluster Initialization
One major part of this work is to enable users to automatically deploy MobilityDB on Azure. Someone can use our software to roll out a MobilityDB cluster along with Citus extension with minimum human interaction. The image below depicts the cluster generation process.
![MobilityDB cluster initialization diagram](readme_images/automaticClusterGeneration.svg)

## Kubernetes Architecture
After deploying the cluster, a Kubernetes deployment should be launched to initialize the corresponding Pods. The following image illustrates the final Kubernetes deployment.
![Kubernetes architecture](readme_images/K8S_Architecture-slides_version.jpg)

## Execution Guidelines

The purpose of this section is to enable the user reuse the existing work.

### Required Components
This work combines different tools and technologies to create a self-managed database on the cloud. The following list includes the required components along with some links that assist the users to install and configure them.

* A local computer running **Linux OS** (tested with Ubuntu 20.04).
* A **Microsoft Azure account** with an active subscription attached to it. The user must have full access to the Azure resources (Owner).
* A Service Principal, created and configured for your Azure account. More details on how to create a Service Principal can be found [here](https://docs.microsoft.com/en-us/azure/developer/python/configure-local-development-environment?tabs=cmd#required-components).

### Cluster Initialization
To deploy a MobilityDB cluster on Azure, follow the below steps:
<ol>
<li>Clone the Github repository</li>
<li>Configure the bash script under the path <strong>MobilityDB-Azure/automaticClusterDeployment/KubernetesCluster/deployK8SCluster.sh</strong>, by modifying the values of the parameters placed on the top of the file in the following way:
    <ul>
    <li><code>AzureUsername</code> parameter is used to login to your Azure account.</li>
    <li>The default <code>ResourceGroupName</code>, <code>Location</code> and <code>VirtualNetwork</code> values can be used.</li>
    <li><code>Subscription</code> defines the name of the active Azure subscription.</li>
    <li><code>VMsNumber</code> determines the number of Worker nodes and <code>VMsSize</code> the size of each machine.</li>
    <li><code>SSHPublicKeyPath</code> and <code>SSHPrivateKeyPath</code> values specify the location of the ssh private and public keys to access the created VMs. By default, the files will be stored in <strong>~/.ssh/</strong> directory.</li>
    <li><code>Gitrepo</code> specifies the Github repository from which the installation scripts and the rest source files will be found. The default value should be used.</li>
    <li><code>Service_app_url</code> determines  the  url  of  the  Service  Principal  and <code>Service_tenant</code> the tenant’s id. When executing the script, the <code>Client secret</code> should be given by the user to authenticate the application in Azure.</li>
    </ul>
</li>
<li>Execute the script by running <code>bash MobilityDB-Azure/automaticClusterDeployment/KubernetesCluster/deployK8SCluster.sh</code>. After around 15 minutes, the cluster will be deployed on Azure.</li>
</ol>

When the cluster is ready, you can access any machine using the `~/.ssh/id_rsa` key. The next step is to establish an ssh connection with the Coordinator VM. To connect to the machine, run `ssh -i ~/.ssh/id_rsa azureuser@{vm_ip_address}`, where vm_ip_address is the public ip address of the Coordinator VM that can be found inAzure portal. When connected to the VM, you can confirm that the K8S cluster has been successfully initialized by executing `sudo kubectl get nodes`.

### Deploying A PostgreSQL Cluster

Until now we have created a Kubernetes cluster on Azure. The purpose of this section is to deploy a PostgreSQL cluster with Citus and MobilityDB extensions installed. First we need to modify the provided configuration files:
<ol>
<li>Edit the content of <strong>MobilityDB-Azure/KubernetesDeployment/postgres-secrets-params.yaml</strong> file by changing the values of the <strong>username</strong> and <strong>password</strong>. These credentials will be the default keys to access the PostgreSQL server.  The values should be provided as base64-encoded strings. To get such an encoding, you can use the following shell command: <code>echo -n "postgres" | base64</code>.</li>
<li>Replace the content of the folder <strong>MobilityDB-Azure/KubernetesDeployment/secrets</strong> by creating your own SSL certificate that Citus will use to encrypt the database data. The existing files can be used for guidance.</li>
<li>Edit the content of <strong>MobilityDB-Azure/KubernetesDeployment/postgres-deployment-workers.yaml</strong> by setting the replicas to be equal to the number of available worker machines that you want to create.</li>
<li>Run <code> bash MobilityDB-Azure/KubernetesDeployment/scripts/startK8s.sh</code> to create the Kubernetes deployment. After some few minutes, the Pods will be created and ready to serve the database.</li>
</ol>

Now you are ready to connect to your distributed PostgreSQL cluster. After connecting to the Coordinator VM, execute the following shell command to ensure that the Pods are running, as show in the following screenshot : `sudo kubectl get pods -o wide`. Normally, you should see one Pod hosting the citus-master and a number of citus-worker Pods, equal to the replica number that you defined before.<br><br>

![alt text](readme_images/pods_screenshot.png)

You can connect to the Citus Coordinator by using the **public ip** of the master VM as **host name/address**, **30001 as port**, **postgres as database** and the **username** and **password** that you defined before. The default values are **postgresadmin** and **admin1234**, respectively. Try to execute some Citus or MobilityDB queries. For instance, run `select master_get_active_worker_nodes()` to view the available Citus worker nodes.

### Self-managed PostgreSQL Cluster

Assuming we have successfully done all the previous step, we are now ready to turn the PostgreSQL database into a self-managed cluster. The process of monitoring and applying an auto-scaling mechanism is managed by a script, implemented as a Daemon process and written in Python 3. To execute the script, follow the step below:

<ol>
<li>Replace   the   parameters   on   the top of the <strong>MobilityDB-Azure/autoscaling/scripts/addNewVms.sh </strong> file with the same parameters that you provided in <strong>MobilityDB-Azure/automaticClusterDeployment/KubernetesCluster/deployK8SCluster.sh</strong>.</li>
<li>Execute <code>sudo -s</code> command on the Coordinator VM to get root access rights.</li>
<li>Create a virtual environment by running <code>python3 -m venv venv</code> and activate it <code>source venv/bin/activate</code></li>
<li>Install the required packages by first running <code>pip install setuptools-rust</code>, <code>export CRYPTOGRAPHY_DONT_BUILD_RUST=1</code> and <code>pip install -r MobilityDB-Azure/autoscaling/requirements.txt</code>.</li>
<li>Export the following environment variables, by adjusting their values as follows:</li>
    <ul>
    <li><code>export AZURE_SUBSCRIPTION_ID=...</code>, <code>export AZURE_TENANT_ID=...</code>, <code>export   AZURE_CLIENT_ID=...</code> and <code>export AZURE_CLIENT_SECRET=...</code> by specifying the corresponding values from the Azure Service Principal.</li>
    <li><code>export RESOURCE_GROUP=...</code> with the Azure resource group name.</li>
    <li><code>export POSTGREDB=postgres</code>, <code>export POSTGREUSER=...</code> and <code>export POSTGREPASSWORD=...</code> with the corresponding server credentials.</li>
    <li><code>export POSTGREPORT=30001</code>.</li>
    <li><code>export SCRIPTPATH=/home/azureuser/MobilityDB-Azure/autoscaling/scripts</code>, assuming you have cloned the source code into /home/azureuser path.</li>
    </ul>
<li>Copy the content of <strong>~/.ssh/id_rsa.pub</strong> file from your local machine to the same path in the Coordinator VM.</li>
<li>Finally, execute the following command to launch the auto-scaler: <code>python3 MobilityDB-Azure/autoscaling/AutoscalingDaemon.py --action start --minvm 2 --maxvm 8 --storage /home/azureuser/autolog --lower_th 70 --upper_th 30 --metric sessions</code>. You can get more information regarding the available parameters by running <code>python3 MobilityDB-Azure/autoscaling/AutoscalingDaemon.py --help</code>. <strong>Note:</strong> the auto-scaler is a Daemon process hence, the script can be executed in the background. Information about the state of the auto-scaler can be found in <strong>/var/log/autoscaling.log</strong> and <strong>/var/log/autoscaling_performance.log</strong> log files.</li>
</ol>
