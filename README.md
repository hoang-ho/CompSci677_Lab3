# Multi-tier Microservices WebApp
Programming Lab2 for the course CS 677: Distributed OS. In this lab we have to implement a microservices architecture using REST APIs. We have to emulate a bookstore running on a single server with a single buyer. The bookstore components (front-end, catalogue and order) are deployed as three processes and a fourth process representing the client performing interface calls to the front-end process.

**Assumption:** As per the documentation, the `search` operation returns only `id and topic` fields and the `lookup` operation returns only `cost and stock` fields.

## To deploy to EC2

### Creating and Running Instances
Create 3 EC2 instances using ami-085ca2d6000e2a2e9 (this is a customized image with docker, docker-composed and git repo cloned and installed).

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

Change the working directory to the repository's root folder

```
$ cd Microservices-Web-App
```

### Setting up the config_env File

For the instance you choose to server the catalog-service, put its Private IPv4 address in the `./config_env` file for the field name `CATALOG_HOST`, similarly update the `ORDER_HOST` for the order-service.

You repeat this step for EC2 instances that you choose to server front-end-service and the order-service as follows:
> NOTE: If you want to change the port, please remember to update the security group, the config_env and the docker-compose file!

```
# Modify the config_env
$ vim config_env
```

### Deploying and Running Containers in EC2 Instances

Now we're done setting up and will start deploying as follows:

In the instance you choose to be front-end-service run

```
$ docker-compose up --build front-end-service
```

In the instance you choose to be catalog-service run

```
$ docker-compose up --build catalog-service
```

In the instance you choose to be order-service run

```
$ docker-compose up --build order-service
```

### Testing from the Client

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
curl --header "Content-Type: application/json" --request PUT  --data '{"id": 1, "stock":2000, "cost":2000}' http://$CATALOG_PUBLIC_IPv4_DNS:5002/catalog/update
```

### Sample Output:

> NOTE: More sample outputs can be found under ./doc/outputs folder

```
curl --request GET $FRONT_END_PUBLIC_IPv4_DNS:5004/search/distributed-systems
{
    "items": {
        "How to get a good grade in 677 in 20 minutes a day.": 1,
        "RPCs for Dummies.": 2
    }
}
```

## Test Scripts for Testing

1. To test services deployed on AWS EC2 instances

    Follow the `To Deploy to EC2 Instance` steps and then run the below command from the client that has the git repo cloned. The output of the test is in a newly created txt file - `out.txt`.
    ```
    $ cd Microservices-Web-App
    $ bash test.sh $FRONT_END_SERVER_PUBLIC_IPv4_DNS $CATALOG_SERVER_PUBLIC_IPv4_DNS
    ```

2. To test services deployed locally

    Follow the `To Deploy to EC2 Instance` steps and then run the below command from the client that has the git repo cloned. The output of the test is in a newly created txt file - `out.txt`.

    > NOTE: Please don't update the `./config_env` file on the client machine to run the tests locally.

    ```
    $ cd Microservices-Web-App
    $ bash test_local.sh
    ```

## Simulating Concurrency

To simulate a concurrency situation with buy and update, run the python file `./SimulateConcurrency.py`. 

> NOTE: Please make sure to have the `requests` library installed on the client.

Sample Output:

```
(base) Hoangs-MacBook-Pro:Microservices-Web-App hoangho$ python3 SimulateConcurrency.py --front-end-dns $FRONT_END_SERVER_PUBLIC_IPv4_DNS  --catalog-dns $CATALOG_SERVER_PUBLIC_IPv4_DNS 

INFO:root:Look up the book stock and cost before update and buy: {
    "cost": 10.0,
    "stock": 1000
}
INFO:root:Main    : create and start thread 0.
INFO:root:Calling request http://ec2-100-25-36-171.compute-1.amazonaws.com/buy/2 at timestamp 1617657154.635759
INFO:root:Main    : create and start thread 1.
INFO:root:Calling request http://ec2-100-25-36-171.compute-1.amazonaws.com/buy/2 at timestamp 1617657154.6362062
INFO:root:Main    : create and start thread 2.
INFO:root:Calling request http://ec2-54-210-80-160.compute-1.amazonaws.com/catalog/update at timestamp 1617657154.636657
INFO:root:Calling request http://ec2-54-210-80-160.compute-1.amazonaws.com/catalog/update at timestamp 1617657154.636717
INFO:root:Main    : before joining thread 0.
INFO:root:Response: {
  "book": "RPCs for Dummies.", 
  "message": "Done update"
}
 at time stamp 1617657154.725301
INFO:root:Response: {
    "message": "successfully purchased the book RPCs for Dummies."
}
 at time stamp 1617657154.74664
INFO:root:Main    : thread 0 done
INFO:root:Main    : before joining thread 1.
INFO:root:Response: {
    "message": "successfully purchased the book RPCs for Dummies."
}
 at time stamp 1617657154.758931
INFO:root:Main    : thread 1 done
INFO:root:Main    : before joining thread 2.
INFO:root:Main    : thread 2 done
INFO:root:Look up the book stock and cost after update and buy: {
    "cost": 2000.0,
    "stock": 1998
}
```

As we can see from the terminal log, we have 2 update requests and 1 buy requests. The two update requests are done first, and thus, the stock for book 2 is set to 2000.0 and its cost is set to 2000.0. When the buy request comes in, the stock is set to 1999 and the cost remains the same!

## Evalation
1. Time to complete 1000 sequential requests by one user
```
INFO:root:Total time: 90191.7736530304
INFO:root:Average time: 90.1917736530304
```
2. Time to complete 1000 sequential requests by 5 user at a time
```
INFO:root:Total time: 136533.04195404053
INFO:root:Average time: 136.53304195404053
```

## Logging on Catalog and Order Services

1. Catalog Service

    Logging happens in `logfile.json` inside the Docker container catalog-service. To check the logs run the following command while the container is running

    ```
    $ docker exec -it catalog-service bash 
    ```

    Inside the container, check the logfile.json:

    ```
    $ cat logfile.json
    ```

    > A buy request will be logged in the "buy" key of the json object. 
    
    > A query request will be logged in the "query" key of the json object. 

2. Order Service

    To view the logs for the order-service call the following request while the container is running

    ```
    curl --header "Content-Type: application/json" --request GET http://$ORDER_PUBLIC_IPv4_DNS:5007/log
    ```

