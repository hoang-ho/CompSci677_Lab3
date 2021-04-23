# Catalog service
## API

The service exposes two API calls: a GET request (query API) and a PUT request (update API).

For milestone 1 & 2, CatalogService has two replicas: one exposed on port 5001 and the other exposed on port 5002

You can run with Docker or you can run locally in your computer. 

To run with Docker:

```
$ docker-compose up --build catalog_service_1 catalog_service_2
```

We implement primary-backup protocol for consistency. Example output:

```
(base) Hoangs-MacBook-Pro:CompSci677_Lab3 hoangho$ curl --request GET http://localhost:5001/info
{
  "coordinator": 123, 
  "node_id": 123
}
(base) Hoangs-MacBook-Pro:CompSci677_Lab3 hoangho$ curl --request GET http://localhost:5002/info
{
  "coordinator": 123, 
  "node_id": 111
}
(base) Hoangs-MacBook-Pro:CompSci677_Lab3 hoangho$ curl --header "Content-Type: application/json" --request PUT  --data '{"id": 1}' http://localhost:5002/catalog/buy
{
    "book": "How to get a good grade in 677 in 20 minutes a day."
}
(base) Hoangs-MacBook-Pro:CompSci677_Lab3 hoangho$ curl --header "Content-Type: application/json" --request GET  --data '{"id": 1}' http://localhost:5001/catalog/query
{
  "cost": 1000.0, 
  "stock": 999
}
(base) Hoangs-MacBook-Pro:CompSci677_Lab3 hoangho$ curl --header "Content-Type: application/json" --request GET  --data '{"id": 1}' http://localhost:5002/catalog/query
{
  "cost": 1000.0, 
  "stock": 999
}
(base) Hoangs-MacBook-Pro:CompSci677_Lab3 hoangho$ curl --header "Content-Type: application/json" --request PUT  --data '{"id": 1, "stock":2000, "cost":2000}' http://localhost:5002/catalog/update
{
    "book": "How to get a good grade in 677 in 20 minutes a day.",
    "message": "Done update"
}
(base) Hoangs-MacBook-Pro:CompSci677_Lab3 hoangho$ curl --header "Content-Type: application/json" --request GET  --data '{"id": 1}' http://localhost:5001/catalog/query
{
  "cost": 2000.0, 
  "stock": 2000
}
(base) Hoangs-MacBook-Pro:CompSci677_Lab3 hoangho$ curl --header "Content-Type: application/json" --request GET  --data '{"id": 1}' http://localhost:5002/catalog/query
{
  "cost": 1000.0, 
  "stock": 2000
}
```