#!/bin/bash
#./launch.sh "launch" "East US 2" "/home/siddhu/workspace/az-keys/example1.pem" "azure-script-launch" 2 "medium" "1" "0.9.0"
action=$1
if [ $action == "launch" ]
then
location=$2
key=$3
service_name=$4
slaves=$5
size=$6
hadoop_version=$7
spark_version=$8
username="sigmoid"
echo "launching cluster"
azure service create --location "South Central US" $service_name

azure vm create --connect $service_name --location "South Central US" --ssh 22 --ssh-cert $key --no-ssh-password --vm-size $size   b39f27a8b8c64d52b05eac6a62ebad85__Ubuntu-14_10-amd64-server-20140923-beta2-en-us-30GB $username

port=44
for i in $(seq 1 $slaves); do 
echo "creating slave" $i "ssh port " $port
azure vm create --connect $service_name --location "South Central US" --ssh $port --ssh-cert $key --no-ssh-password --vm-size $size b39f27a8b8c64d52b05eac6a62ebad85__Ubuntu-14_10-amd64-server-20140923-beta2-en-us-30GB $username
port=$(( port+11 ))
done

echo "Successfully launched cluster...setting up machines"
python setup.py $service_name $slaves $hadoop_version $spark_version $key

echo "setting endpoints..."
azure vm endpoint create $service_name 50070 50070
azure vm endpoint create $service_name 5050 5050
azure vm endpoint create $service_name 8080 8080
azure vm endpoint create $service_name 4040 4040

#./launch.sh "destroy" "azure-script-final3"
elif [ $action == "destroy" ]
then
echo "destroying..."$2
azure service delete $2

#./launch.sh "endpoint" "azure-script-final3" "8081" "8081"
elif [ $action == "endpoint" ]
then 
echo "creating endpoints"
azure vm endpoint create $2 $3 $4
fi
