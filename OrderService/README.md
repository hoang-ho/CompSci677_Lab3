# Order Service
The order server supports a single operation: buy(item_number). Upon receiving a buy request, the order server must first verify that the item is in stock by querying the catalog server and then decrement the number of items in stock by one. The buy request can fail if the item is out of stock.

The buy request takes as a book id as input. If the id is not valid and the book is not present it returns an error messaege.
If the id is present, it sends a query to the cataloge service. If the stock >0 it sends a update request with -1 to the cataloge service. Otherwise the buy request fails.

Call buy
curl --header "Content-Type: application/json" --request PUT  --data '{"id": 3}' http://localhost:5007/order

View logs
curl --header "Content-Type: application/json" --request GET   http://localhost:5007/log

Calling from docker
requests.put("http://order-service:5007/order", json={"id": 1})

