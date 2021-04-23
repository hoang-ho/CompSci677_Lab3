# CompSci 677 Lab 3

## Mileston 1 and 2

To run the services in the detached mode, run the following command:

```
$ docker-compose up --build -d
```

Also, to run only a particular container run the following command:

```
$ docker-compose up --build <service-name>
```

### Available commands to run from the client
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

### System Description

#### Memcache

#### Load-Balancer

#### Database Consistency
