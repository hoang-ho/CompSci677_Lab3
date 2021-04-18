# Front End Service

This service exposes all the API endpoints that the users will be able to interact with. It is also responsible for the processing and abstracting back-end servers from the users. Based on the API the front-end service decides to call the catalog service or the order service.

## Endpoints Available

1. **Search(topic):**
> API Endpoint: GET http://localhost:5004/search/topic-name

This allows the user to specify a topic and returns the name and the id of all entries belonging to that category. The topic is a string and available topics are: `distributed-systems` and `graduate-school`. This is turn calls the query functionality of catalog service.

2. **Lookup(id):**
> API Endpoint: GET http://localhost:5004/lookup/book-id

This allows an id to be specified and returns the number of items in stock and cost of the book with id=book-id. The id is in the list: `1, 2, 3, and 4`. This is turn calls the query functionality of catalog service.

3. **Buy(id):**
> API Endpoint: POST http://localhost:5004/buy/book-id

This specifies a book id for purchase. This in turn calls the order service.

## Running the service locally

**Prerequisites:** Please make sure that docker is installed and running locally.

To deploy locally, git clone the repo. Then perform the following steps in the mentioned order:

```
1. $ cd Microservices-web-app
2. $ docker-compose up -d --build front-end-service
```

Alternatively, you could also cd into this folder: `./FrontendService/deployments` and run the following command

```
1. $ docker build -t front_end_service
2. $ docker run -p 5004:5004 front_end_service
```

### Examples of available commands to run from the client
**Prerequisites:** Please make sure the environment is runnning by following the above commands.

1. To get the list of all endpoints available
```
$ curl --request GET http://localhost:5004/
```

1. To search for books by topic:

```
$ curl --request GET http://localhost:5004/search/distributed-systems
```

2. To lookup books by id:
```
$ curl --request GET http://localhost:5004/lookup/1
```

3. To buy a book by id:
```
$ curl --request POST http://localhost:5004/buy/2 
```

### Stopping and Removing the Containers
To stop and remove containers and images run the following command:

```
$ docker-compose down -v --rmi all --remove-orphans
```