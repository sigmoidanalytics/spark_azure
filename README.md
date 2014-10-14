##Setting up azure command line tool and launching cluster on azure
To install the tool on Linux, install the latest version of Node.JS and then use NPM to install:

####Install node.js
```
sudo apt-get update
sudo apt-get install nodejs
sudo apt-get install npm
```

####Install tool 
```
npm install azure-cli -g

azure --help
```
####Subscribing to azure
```
azure account import BizSpark\ Plus-9-19-2014-credentials.publishsettings
```
####Generate key
```
openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout example1.key -out example1.pem

chmod 600 example1.key
```
####Using launch.sh to launch cluster 
```
./launch.sh "action" "South Central US" "example1.pem" "-vm-name" <-no_of_slaves(minimum 1)> "vm-size" "hadoop_major_version" "spark_version"

Ex: ./launch.sh "launch" "South Central US" "~/example1.pem" "azure-script-launch" 2 "medium" "1" "0.9.0"

hadoop_major version can be 1 or 2
spark versions can be 0.9.0 or 1.1.0
vm-size valid values are "extrasmall", "small", "medium", "large", "extralarge", a5, a6, a7, a8, a9
action can be launch, destroy, endpoint

```
####SSH master
```
ssh -i ~/example1.key sigmoid@<-vm-name>.cloudapp.net -p 22
```
_workers can be accessed using ports 44 55 66...._

#####If problem exists while ssh run this command
ssh-keygen -f "/home/siddhu/.ssh/known_hosts" -R <dns-name>

####Destroying cluster
```
./launch.sh "destroy" "vm-name"
```
####Creating Endpoints
```
./launch.sh "endpoint" "vm-name" "8081" "8081"
```
