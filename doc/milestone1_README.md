## Milestone 1

**Deliverables:** A bookstore running on a single server with a single buyer. The bookstore components (front-end, catalogue and order) are deployed as three processes and a fourth process representing the client performing interface calls to the front-end process.

**Assumption:** As per the documentation, the `search` operation returns only `id and topic` fields and the `lookup` operation returns only `cost and stock` fields.

### Overview 
The following is a brief description of each microservice implemented.

- Front End Server: The users will interact with this server. It is responsible for the processing and abstracting back-end servers from the users. The implementation of this server is under the folder `./FrontendService`. It consists of only one microservice that has the functionality of search for a book by topic, looking up for a book by it's id and buying the book by it's id.

- Catalog Server: This in one of the microservices that forms the back-end server. It is responsible of maintaining the catalog of the books availables and the cost and quantity of the books. Also, it implements the functionality of querying the catalog by `topic or id` and also updating the cost and quantity of books available. The implementation of this microservice is under the folder `./CatalogService`.

- Order Server: This is the second microservice in the back-end server. It is responsible for updating the quantity of the books available everytime it receives a request if the book is available in the catlaog. It also maintains a log of all the purchase orders it receives. The implementation of this microservice is under the folder `./OrderService`.

> Note: For more details on each service, please refer the individual README files in the folders.

### Setting up the code locally
**Prerequisites:** Please make sure that docker is installed and running locally.

To deploy locally, git clone the repo. Then perform the following steps in the mentioned order:

```
1. $ cd Microservices-web-app
2. $ docker-compose up --build -d
```

The last command will build images and run containers for each of the services in detach mode.

To run the services in the foreground run the following command:

```
$ docker-compose up --build
```

Also, to run only a particular container run the following command:

```
$ docker-compose up --build <service-name>
```
> Note: The available services are: front-end-service, catalog-service, order-service.

### Available commands to run from the client
**Prerequisites:** Please make sure the environment is runnning by following the above commands.

1. To search for books by topic:
> API Endpoint: GET http://localhost:5004/search/topic-name

```
$ curl --request GET http://localhost:5004/search/distributed-systems
{
    "items": {
        "How to get a good grade in 677 in 20 minutes a day.": 1,
        "RPCs for Dummies.": 2
    }
}
```
```
$ curl --request GET http://localhost:5004/search/graduate-school 
{
    "items": {
        "Cooking for the Impatient Graduate Student.": 4,
        "Xen and the Art of Surviving Graduate School.": 3
    }
}
```

2. To lookup books by id:
> API Endpoint: GET http://localhost:5004/lookup/book-id

```
$ curl --request GET http://localhost:5004/lookup/1
{
    "cost": 1.0,
    "stock": 1000
}
```

3. To buy a book by id:
> API Endpoint: POST http://localhost:5004/buy/book-id

```
$ curl --request POST http://localhost:5004/buy/2 
{
    "message": "book bought successful"
}
```

4. To hit the catalog service directly to update the cost or the stock of an item
   
```
$ curl --header "Content-Type: application/json" --request PUT  --data '{"id": 1, "stock":2000, "cost":2000}' http://localhost:5002/catalog/update
{
  "success": true
}
```

### Stopping and Removing the Containers
To stop and remove containers and images run the following command:

```
$ docker-compose down -v --rmi all --remove-orphans
```

### Test Script
Run test.sh to test the APIs. The output of the test is in a newly created txt file, out.txt.

### Logging for CatalogService

Logging happens in logfile.json inside the Docker container catalog-service, to check if the logging is there:

```
$ docker exec -it catalog-service bash 
```

Inside the container, check the logfile.json:

```
$ cat logfile.json
```

A buy request will be logged in the "buy" key of the json object. A query request will be logged in the "query" key of the json object. 