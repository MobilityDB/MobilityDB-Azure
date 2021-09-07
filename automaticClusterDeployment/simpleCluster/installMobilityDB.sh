#!/bin/bash
currentpath="/home/azureuser"

wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
RELEASE=$(lsb_release -cs)
echo "deb http://apt.postgresql.org/pub/repos/apt/ ${RELEASE}"-pgdg main | sudo tee  /etc/apt/sources.list.d/pgdg.list
sudo apt update

################################################################################
#				Install the required software for MobilityDB				   #
################################################################################
yes | sudo apt install postgresql-server-dev-13
yes | sudo apt install postgis postgresql-13-postgis-2.5
yes | sudo apt install libproj-dev
yes | sudo apt install libjson-c-dev
yes | sudo apt  install cmake
yes | sudo apt-get install build-essential
yes | sudo apt install liblwgeom-dev
yes | sudo apt-get install libgsl-dev
################################################################################


################################################################################
#						 Install MobilityDB						   	           #
################################################################################
yes | sudo apt install git-all
sudo git clone https://github.com/MobilityDB/MobilityDB $currentpath/MobilityDB
sudo mkdir $currentpath/MobilityDB/build
cd $currentpath/MobilityDB/build
#sudo cmake ..
sudo cmake $currentpath/MobilityDB
sudo make
sudo make install
sudo -i -u postgres psql -c 'CREATE EXTENSION MobilityDB CASCADE'
################################################################################


################################################################################
#						Install and Configure Citus					   		   #
################################################################################
curl https://install.citusdata.com/community/deb.sh | sudo bash
sudo apt-get -y install postgresql-13-citus-9.5
sudo pg_conftool 13 main set shared_preload_libraries 'citus,postgis-2.5.so'
sudo pg_conftool 13 main set max_locks_per_transaction 128
sudo pg_conftool 13 main set listen_addresses '*'

#Accept incoming connections from coordicator's ip only
#sudo sh -c 'echo "host\tall\t\tall\t\t51.103.24.166/8\t\ttrust" >> /etc/postgresql/13/main/pg_hba.conf'

#Accept incoming connections from everyone
sudo sh -c 'echo "host\tall\t\tall\t\t0.0.0.0/0\t\ttrust" >> /etc/postgresql/13/main/pg_hba.conf'

#Start the db server
sudo service postgresql restart
#and make it start automatically when computer does
sudo update-rc.d postgresql enable
# add the citus extension
sudo -i -u postgres psql -c "CREATE EXTENSION citus;"
################################################################################