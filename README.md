# Milestone 1
**Deliverables:** In this milestone we had to extend the previous programming lab 2 to implement features such as - Caching and it's invalidation, load balancing at the front end server and replication and consistency of the catalog server and the order server.
**Assumption:** As per the documentation, we have implemented an in-memory cache implementation. The cache invalidation is a server side push technique. Also, 2 replicas are implemented for the catalog and the order server.

## Technical Overview

The following section briefly describes the implementation details of the features implemented in the Microservice. Here, the most basic techniques are used to implement the features because the application is not data intensive and the architecture is not that complex.

### Caching and Invalidation of Caching

A simple in memory dictionary acts as a cache at the front end server. Here, when the front end receives the request it first checks if the data is present in cache. If it is present it returns the cached result to the client, else it forwards the request to the appropriate server and caches the response and returns it to the client.

Also, the front end server has an API endpoint to invalidate the cache. Everytime a request makes an update to the database, before writing the changes to the database, the catalog server calls this endpoint to invalidate the cache if it exists on the front end and then writes the changes to the database.

### Load Balancer at Frontend Server

A simple round robin algorithm is used to implement the load balancer. The round robin algorithm guarantees that all the servers has the same workload. To gurantee this, alternate requests are sent to different replicas.

### Database Replication and Consistency

To maintain consistency across the two different replicas of catalog server, we have implemented a `Primary-Backup` protocal. Moreover, to decide the Primary server we are using the Bully algorithm to elect the primary catalog server.

## Setting up the environment locally

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

## Testing from the Client

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


## Test Scripts for Testing Locally

> NOTE: Please don't update the `./config_env` file on the client machine to run the tests locally.

```
$ cd CompSci677_Lab3
```
```
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
    curl --header "Content-Type: application/json" --request GET http://localhost:5007/log
    ```

