# Catalog service
## API

The service exposes two API calls: a GET request (query API) and a PUT request (update API).

You can run with Docker or you can run locally in your computer. 

To run with Docker:

```
$ docker build -t catalog_service .
```

```
$ docker run -p 5002:5002 catalog_service
```

**Query request**:

In terminal:

```
$ curl --header "Content-Type: application/json" --request GET  --data '{"topic":"distributed systems"}' http://localhost:5002/catalog/query
{
    "items": {
        "How to get a good grade in 677 in 20 minutes a day.": 1,
        "RPCs for Dummies.": 2
    }
}
```

```
$ curl --header "Content-Type: application/json" --request GET  --data '{"title":"graduate school"}' http://localhost:5002/catalog/query
{
    "items": {
        "Cooking for the Impatient Graduate Student.": 4,
        "Xen and the Art of Surviving Graduate School.": 3
    }
}
```

```
$ curl --header "Content-Type: application/json" --request GET  --data '{"id": 1}' http://localhost:5002/catalog/query
{
    "cost": 1.0,
    "stock": 1000
}
```

In python

```python
>>> import requests
>>> r = requests.get("http://localhost:5002/catalog/query", json={"topic":"distributed systems"}) 
>>> r.text
'{
    "items": {
        "How to get a good grade in 677 in 20 minutes a day.": 1,
        "RPCs for Dummies.": 2
    }
}'
>>> r = requests.get("http://localhost:5002/catalog/query", json={"id": 1}) 
>>> r.text
'{
    "cost": 1.0,
    "stock": 1000
}'
```

**Buy request**:

Here, I assume that we use the book id above to buy. However, we can discuss about this!

In terminal, 

```
$ curl --header "Content-Type: application/json" --request PUT  --data '{"id": 1}' http://localhost:5002/catalog/buy
{
  "success": true
}
```

**Update request**

To directly hit the catalog service to update the stock or the cost of an item:

In terminal:

```
$ curl --header "Content-Type: application/json" --request PUT  --data '{"id": 1, "stock":2000, "cost":2000}' http://localhost:5002/catalog/update
{
  "success": true
}
```

In python,

```python
>>> r = requests.put("http://localhost:5002/catalog/update", json={"id": 1}) 
>>> r.text
'{\n  "success": true\n}\n'
```

## Logging

Logging happens in logfile.json inside the Docker container catalog-service, to check if the logging is there:

```
$ docker exec -it catalog-service bash 
```

Inside the container, check the logfile.json:

```
$ cat logfile.json
```

A buy request will be logged in the "buy" key of the json object. A query request will be logged in the "query" key of the json object. 

## Concurrency

To maintain concurrency in the buy and update request, I write a python decorator to synchronized concurrent write requests to the log file as well as to synchronized the access to the update_data function, which is called inside the buy and update request to access and update the database. With the synchronized decorator, it's guaranteed that only one thread can write to the log at a time and only one thread can access the database at a time.

```
def synchronized(func):

    func.__lock__ = threading.Lock()

    def synced_func(*args, **kws):
        with func.__lock__:
            return func(*args, **kws)

    return synced_func

@synchronized
def log_request(newData, key):
    fd = open('logfile.json', "r+")
    data = json.loads(fd.read())
    data[key].append(newData)
    fd.seek(0)
    json.dump(data, fd)
    fd.truncate()
    fd.close()


@synchronized
def update_data(json_request):
    book = session.query(Book).filter_by(id=json_request["id"]).one()

    if ("stock" in json_request):
        book.stock = json_request["stock"]

    if ("cost" in json_request):
        book.cost = json_request["cost"]

    if (json_request["buy"]):
        book.stock -= 1

    logRequest = {"id": book.id, "stock": book.stock,
                  "cost": book.cost, "timestamp": time.time()}
    log_request(logRequest, "update")

    return book.title
```