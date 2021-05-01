# Lab 3: Implementing Caching, Consistency and Fault Tolerance
**Deliverables:** This lab extends the previous programming lab 2 to implement features such as - Caching and it's invalidation, load balancing at the front end server and replication and consistency of the catalog server and the order server. We also, make the system fault tolerant by handling crashes and synchronizing the database during recovery.

The working of the system is explained in detail in the `Design_Document` file under the `/docs` folder.

**Assumption:** 
- We have at most 3 replicas and at most 1 replica can crash
- No failure happens during starting up and recovery period
- Our communication channel is stable and synchronous, and no message is lost
- No replica is significantly slower than others
- Replica can reliably detect who the crash process is

## To deploy to EC2 using Docker

### Creating and Running Instances
Create 7 EC2 instances using ami-00d30e14232a718f0 (this is a customized image with docker, docker-composed and git repo cloned and installed).

> NOTE: If you want to use your own ami, you will need to set up docker, git and security group beforehand

```
$ aws ec2 run-instances --image-id ami-085ca2d6000e2a2e9 --instance-type t2.micro --key-name 677kp
$ aws ec2 describe-instances --instance-id $INSTANCE_ID
```

From the last command, save down the Public IPv4 DNS and the Private IPv4 addresses for each instance. Next, ssh into the instance

### Updating the Security Group Settings

Confirm the rules for incoming traffic as follows. In the Inbound rules section, create the following rules (choose Add rule for each new rule):

- Choose HTTP from the Type list, port 80 for port range, and make sure that Source is set to Anywhere (0.0.0.0/0).
- Choose HTTPS from the Type list, port 443 for port range, and make sure that Source is set to Anywhere (0.0.0.0/0).
- Choose Custom TCP from the Type list, 5000-6000 for Port Range, and make sure that Source is set to Anywhere (0.0.0.0/0).

### Setting up the Instances

ssh into each of the instance as follows:

```
$ ssh -i <path-to-677kp.pem-file> ec2-user@$PUBLIC_IPv4_DNS
```

### Setting up the config_env File - Need to better frame this section

Please create a config file before running the docker image. Sample config files for each replicas of catalog_service and order_service and also config file for the front_end_service can be found in the github repo under the `./env` folder.

> NOTE: If you want to change the port, please remember to update the security group, the config_env and the docker-compose file!

> NOTE: Please make sure to replace the variables' value with the Private IPv4 address of the respective instance

```
# Create the config_env
$ vim config_env
```

Sample Config File for front_end_service

```
CATALOG_HOST_1=172.31.55.197
CATALOG_HOST_2=172.31.53.160
CATALOG_HOST_3=172.31.62.123
CATALOG_PORT=5002
ORDER_HOST_1=172.31.60.146
ORDER_HOST_2=172.31.50.184
ORDER_HOST_3=172.31.54.32
ORDER_PORT=5007
```

Sample Config File for catalog_service_3

```
PROCESS_ID=114
ALL_IDS=123,111,114
ALL_HOSTNAMES=172.31.55.197,172.31.53.160,172.31.62.123
CATALOG_PORT=5002
FRONTEND_HOST=172.31.62.71
FRONTEND_PORT=5004
```

Sample Config File for order_service_3

```
CATALOG_HOST_3=172.31.62.123
CATALOG_PORT=5002
```

### Deploying and Running Containers in EC2 Instances

Now we're done setting up and will start deploying as follows:

In the instance you choose to be front-end-service run

```
$ docker run --env-file <path_to_env_file>/<file_name> -p 5004:5004 --name front_end_service hoangho/front_end_service
```

In the instance you choose to be catalog-service-1 run

```
$ docker run --env-file <path_to_env_file>/<file_name> -p 5002:5002 --name catalog_service_1 hoangho/catalog_service
```

In the instance you choose to be catalog-service-2 run

```
$ docker run --env-file <path_to_env_file>/<file_name> -p 5002:5002 --name catalog_service_2 hoangho/catalog_service
```

In the instance you choose to be catalog-service-3 run

```
$ docker run --env-file <path_to_env_file>/<file_name> -p 5002:5002 --name catalog_service_3 hoangho/catalog_service
```

In the instance you choose to be order-service-1 run

```
$ docker run --env-file <path_to_env_file>/<file_name> -p 5007:5007 --name order_service_1 hoangho/order_service
```

In the instance you choose to be order-service-2 run

```
$ docker run --env-file <path_to_env_file>/<file_name> -p 5007:5007 --name order_service_2 hoangho/order_service
```

In the instance you choose to be order-service-3 run

```
$ docker run --env-file <path_to_env_file>/<file_name> -p 5007:5007 --name order_service_3 hoangho/order_service
```

## Setting up the environment locally

### Directly Downloading from Docker

Follow the following steps to set up the environment:

1. Create a network for docker containers to communicate:
```
docker network create -d bridge my-bridge-network
```

2. Create individual containers for all the micro services and the replicas as follows:
> Note: Please have an environment file for every container. The environment file can be download from the ./env folder for each container also.

```
docker run --env-file <path_to_env_file>/catalog_service_1 -p 5001:5002 --network my-bridge-network --name catalog_service_1 hoangho/catalog_service
```
```
docker run --env-file <path_to_env_file>/catalog_service_2 -p 5002:5002 --network my-bridge-network --name catalog_service_2 hoangho/catalog_service
```
```
docker run --env-file <path_to_env_file>/catalog_service_3 -p 5003:5002 --network my-bridge-network --name catalog_service_3 hoangho/catalog_service
```
```
docker run --env-file <path_to_env_file>/order_service_1 -p 5007:5007 --network my-bridge-network --name order_service_1 hoangho/order_service
```
```
docker run --env-file <path_to_env_file>/order_service_2 -p 5006:5007 --network my-bridge-network --name order_service_2 hoangho/order_service
```
```
docker run --env-file <path_to_env_file>/order_service_3 -p 5005:5007 --network my-bridge-network --name order_service_3 hoangho/order_service
```
```
docker run --env-file <path_to_env_file>/front_end_service -p 5004:5004 --network my-bridge-network --name front_end_service hoangho/front_end_service
```

### Running from the GitHub Repository

Clone the repo and run the following commands:

```
$ cd CompSci677_Lab3
```
```
$ docker-compose up --build
```

> Note: To run a particular container use the following command: docker-compose up --build container-name

To remove all the stopped containers

```
docker-compose down -v --rmi all --remove-orphans
```

### Testing from the Client
**Prerequisites:** Please make sure the environment is runnning by following the above commands.

> NOTE: If running locally the host would be localhost instead of Public IPv4 Address

From your local machine, to test the API run the following commands

```
$ curl --request GET $FRONT_END_PUBLIC_IPv4_DNS:5004/search/<topic_name>
```

```
$ curl --request POST $FRONT_END_PUBLIC_IPv4_DNS:5004/buy/<book_id>
```

```
$ curl --request GET $FRONT_END_PUBLIC_IPv4_DNS:5004/lookup/<book_id>
```

```
curl --header "Content-Type: application/json" --request PUT  --data '{"book_id": 1, "request_id": 123 "stock":2000, "cost":2000}' http://$CATALOG_PUBLIC_IPv4_DNS:5002/catalog/update
```

## Sample Output

> NOTE: More sample outputs can be found under ./doc/sample_output.txt folder

```
$ curl --request GET http://localhost:5004/search/distributed-systems
{
    "items": {
        "How to finish Project 3 on time.": 5,
        "How to get a good grade in 677 in 20 minutes a day.": 1,
        "RPCs for Dummies.": 2,
        "Why theory classes are so hard.": 6
    }
}
```

## Test Scripts for Testing Locally

> NOTE: If setting and running from the GitHub Repository please don't update the `./config_env` file on the client machine to run the tests locally.

> NOTE: If setting and running by pulling images directly from the Dockerhub Repositry please make sure that all the containers are running.

```
$ bash <path_to_file>/test_local.sh
```
