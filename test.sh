# sh file to run the tests after deploying on AWS EC2 instances

frontend=$1
catalog=$2

echo "AWS EC2 Instance Testing "

echo "Search request for topic: distributed systems " >> out.txt

curl --request GET http://${frontend}:5004/search/distributed-systems >> out.txt

echo "Search request for topic: graduate school " >> out.txt

curl --request GET http://${frontend}:5004/search/graduate-school >> out.txt

echo "Lookup request for book id 1 " >> out.txt

curl --request GET http://${frontend}:5004/lookup/1 >> out.txt 

echo "Buy request for book id 1 " >> out.txt

curl --request POST http://${frontend}:5004/buy/1 >> out.txt 

echo "Lookup request for book id 1 " >> out.txt

curl --request GET http://${frontend}:5004/lookup/1 >> out.txt 

echo "Directly update the catalog for book id 1 " >> out.txt

curl --header "Content-Type: application/json" --request PUT  --data '{"id": 1, "stock":2000, "cost":2000}' http://${catalog}:5002/catalog/update >> out.txt

echo "Lookup request for book id 1 " >> out.txt

curl --request GET http://${frontend}:5004/lookup/1 >> out.txt 

echo "Concurrent buy request " 

python3 SimulateConcurrency.py --front-end-dns ${frontend} --catalog-dns ${catalog}
