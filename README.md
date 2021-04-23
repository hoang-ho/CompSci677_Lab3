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

## Available commands to run from the client
**Prerequisites:** Please make sure the environment is runnning by following the above commands.


1. To search for books by topic:
> API Endpoint: GET http://localhost:5004/search/topic-name

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

```
$ curl --request GET http://localhost:5004/search/graduate-school 
{
    "items": {
        "Cooking for the Impatient Graduate Student.": 4,
        "Spring in Pioneer Valley.": 7,
        "Xen and the Art of Surviving Graduate School.": 3
    }
}
```

2. To lookup books by id:
> API Endpoint: GET http://localhost:5004/lookup/book-id

```
$ curl --request GET http://localhost:5004/lookup/1
{
    "cost": 1000.0,
    "stock": 1000
}
```

3. To buy a book by id:
> API Endpoint: POST http://localhost:5004/buy/book-id

```
$ curl --request POST http://localhost:5004/buy/2 
{
    "message": "successfully purchased the book How to get a good grade in 677 in 20 minutes a day."
}
```

4. To hit the catalog service directly to update the cost or the stock of an item
   
```
$ curl --header "Content-Type: application/json" --request PUT  --data '{"id": 1, "stock":2000, "cost":2000}' http://localhost:5002/catalog/update
{
    "book": "How to get a good grade in 677 in 20 minutes a day.",
    "message": "Done update"
}

$ curl --request GET http://localhost:5004/lookup/1
{
    "cost": 2000.0,
    "stock": 2000
}
```

## Test Scripts for Testing Locally

> NOTE: Please don't update the `./config_env` file on the client machine to run the tests locally.

```
$ cd CompSci677_Lab3
```
```
$ bash test_local.sh
```

## Database Consistency

For milestone 1 & 2, CatalogService has two replicas: one exposed on port 5001 and the other exposed on port 5002.
