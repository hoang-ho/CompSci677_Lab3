# sh file to run the test cases on localhost

echo "Local Testing"

echo "Search request for topic: distributed systems " >> out.txt

curl --request GET http://localhost:5004/search/distributed-systems >> out.txt

echo "Search request for topic: graduate school " >> out.txt

curl --request GET http://localhost:5004/search/graduate-school >> out.txt

echo "Lookup request for book id 1 " >> out.txt

curl --request GET http://localhost:5004/lookup/1 >> out.txt 

echo "Buy request for book id 1 " >> out.txt

curl --request POST http://localhost:5004/buy/1 >> out.txt 

echo "Lookup request for book id 1 " >> out.txt

curl --request GET http://localhost:5004/lookup/1 >> out.txt 

echo "Directly update the catalog for book id 1 " >> out.txt

curl --header "Content-Type: application/json" --request PUT  --data '{"id": 1, "stock":2000, "cost":2000}' http://localhost:5002/catalog/update >> out.txt

echo "Lookup request for book id 1 " >> out.txt

curl --request GET http://localhost:5004/lookup/1 >> out.txt 

