from flask import request, jsonify
from flask_restful import Api, Resource
from database.database_setup import Base, Book, session
from ConsistencyProtocol.PrimaryBackup import Node, BeginElection
from utils import synchronized, log_write_request, log_read_request
from sys import stdout
import logging
import threading
import json
import time
import os
import requests

CATALOG_PORT = os.getenv("CATALOG_PORT")

FRONTEND_HOST = os.getenv("FRONTEND_HOST")
FRONTEND_PORT = os.getenv("FRONTEND_PORT")

logger = logging.getLogger("Catalog-Service")

logger.setLevel(logging.INFO)  # set logger level
logFormatter = logging.Formatter(
    "%(name)-12s %(asctime)s %(levelname)-8s %(filename)s:%(funcName)s %(message)s")
consoleHandler = logging.StreamHandler(stdout)  # set streamhandler to stdout
consoleHandler.setFormatter(logFormatter)
logger.addHandler(consoleHandler)

node = Node()

@synchronized
def update_data(update_request):
    '''
    update_request: a request of type json that contains id to query book by id and update/buy the book
    This is a synchronized function
    '''
    # update the current database as well as the base_database log
    book = session.query(Book).filter_by(id=update_request["book_id"]).one()
    fd = open('base_database.json', "r+")
    data = json.loads(fd.read())
    key = "book_id_%s" % str(update_request["book_id"])
    
    if (update_request["request_type"] == "buy"):
        book.stock -= 1
        data[key]["stock"] -= 1
    elif (update_request["request_type"] == "update"):
        if (update_request.get("stock", None)):
            book.stock = update_request["stock"]
            data[key]["stock"] = update_request["stock"]
        
        if (update_request.get("cost", None)):
            book.cost = update_request["cost"]
            data[key]["cost"] = update_request["cost"]

    fd.seek(0)
    json.dump(data, fd)
    fd.truncate()
    fd.close()

    return book.title


def wrapper_put_request(endpoint, update_request):
    try:
        response = requests.put(endpoint, json=update_request, timeout=3.05)
        if response.status_code == 200:
            return response
        else:
            return None
    except:
        logger.info(f'Node not alive at: {endpoint}')

    return None


def handle_write_request(write_request):
    node.lock.acquire()
    # Write to log
    log_write_request(write_request)

    # propagate update to other replicas
    write_request["coordinator"] = node.node_id
    propagateUpdates(write_request)

    # execute the update
    title = update_data(write_request)
    node.lock.release()
    return title


def prepopulate():
    '''
    Initialzing the database with the data
    '''
    if (session.query(Book).first() is None):
        f = open('base_database.json', "r")
        data = json.loads(f.read())

        # add all the book
        for key,book in data.items():
            session.add(Book(
                id=book['id'], title=book["title"], topic=book["topic"], stock=book["stock"], cost=book["cost"]))
        session.commit()


def propagateUpdates(update_request):
    '''
    This function sends the write updates to all the running replicas in the system
    '''
    threads = list()
    logger.info(f"Propagate updates to other replicas {node.alive_neighbors}")
    for neighbor, url in node.alive_neighbors.items():
        if (int(neighbor) != node.node_id):
            endpoint = f"http://{url}:{CATALOG_PORT}/update_database"
            t = threading.Thread(target=wrapper_put_request,
                                 args=(endpoint, update_request))
            threads.append(t)
            t.start()
    
    for t in threads:
        t.join()


def push_invalidate_cache(id):
    '''
    A server-push technique to invalidate the cache in front-end before writing to database
    '''
    t_start = time.time()
    data = {'id': id}
    url = f"http://{FRONTEND_HOST}:{FRONTEND_PORT}/invalidate-cache"
    requests.post(url, json=data)
    t_end = time.time()
    t_diff = t_end - t_start
    logger.info(f"Invalidate cache overhead {t_diff}")


def push_data():
    '''
    A helper function to sync database between joining replica and primary
    '''
    node.lock.acquire()
    books = session.query(Book).all()
    json_data = {"Books": [book.serializeAll for book in books]}
    logger.info(f"Sending data {json_data}")
    node.announce(json_data)
    node.lock.release()


class HealthCheck(Resource):
    '''
    Endpoint to check if the node is running
    '''
    def get(self):
        response = jsonify({'message': 'OK'})
        response.status_code = 200
        return response

      
class Query(Resource):
    def get(self):
        '''
        Handle get request for search by topic and lookup by id
        '''
        books = []
        request_data = request.get_json()
        if (request_data and ("id" in request_data or "topic" in request_data)):
            if ("id" in request_data):
                books = session.query(Book).filter_by(id=request_data["id"]).all()
                if (len(books) == 0):
                    response = jsonify(success=False)
                    response.status_code = 400
                else:
                    request_data["time_stamp"] = time.time()
                    log_read_request(request_data)
                    response = jsonify(books[0].serializeQueryById)
                    response.status_code = 200

            elif ("topic" in request_data):
                books = session.query(Book).filter_by(topic=request_data["topic"]).all()
                request_data["time_stamp"] = time.time()
                log_read_request(request_data)
                response = jsonify(items={book.title: book.id for book in books})
                response.status_code = 200
        else:
            response = jsonify(success=False)
            response.status_code = 400

        return response

      
class Buy(Resource):
    def put(self):
        '''
        For a buy request, forward the request to the primary replica
        '''
        json_request = request.get_json()

        # Checks if the operation is already performed in case of a crash
        query_id=json_request['request_id']
        fd = open('write_requests.json', "r+")
        data = json.loads(fd.read())
        target_key = "request_id_" + str(query_id)
        if target_key in data:
            book_id = json_request['book_id']
            book = session.query(Book).filter_by(id=book_id).one()
            response = jsonify(book=book.title)
            response.status_code = 200
            return response

        # Buy request execution
        if (node.node_id == node.coordinator):
            # if we are the primary
            if ("book_id" in json_request):

                # Invalidating the cache before writing to database
                push_invalidate_cache(json_request['book_id'])

                json_request["request_type"] = "buy"
                title = handle_write_request(json_request)

                # send back a response
                response = jsonify(book=title)
                response.status_code = 200
                return response
            else:
                response = jsonify(success=False)
                response.status_code = 400
                return response
        else:
            # forward request to primary
            primary = node.coordinator
            url = node.neighbors[primary]
            endpoint = f"http://{url}:{CATALOG_PORT}/catalog/buy"
            response = requests.put(endpoint, json=json_request)
            if (response.status_code == 200):
                return response.json(), 200
            else:
                return response.json(), 500

              
class PrimaryUpdate(Resource):
    def put(self):
        '''
        Handle update request sent from primary server
        '''
        json_request = request.get_json()
        if (json_request.get("coordinator", -1) != node.coordinator):
            json_response = {"message": "Update not successful"}
            response = jsonify(json_response)
            response.status_code = 400
            return response

        if (json_request and "book_id" in json_request):
            # Writing to database
            json_request["buy"] = False
            log_write_request(json_request)
            title = update_data(json_request)

            json_response = {"message": "Done update", "book": title}
            response = jsonify(json_response)
            response.status_code = 200
            return response
        else:
            json_response = {"message": "Update not successful"}
            response = jsonify(json_response)
            response.status_code = 400
            return response


class Update(Resource):
    def put(self):
        '''
        Handle put request for update
        Return 200 if update succeeds
        '''
        json_request = request.get_json()
        
        # if we are the coordinator
        if (node.node_id == node.coordinator):
            # update the database and propagate it to all replicas
            if (json_request and "book_id" in json_request):
                # Invalidating the cache before writing to database
                push_invalidate_cache(json_request['book_id'])

                json_request["request_type"] = "update"
                title = handle_write_request(json_request)

                json_response = {"message": "Done update", "book": title}
                response = jsonify(json_response)
                response.status_code = 200
                return response
            else:
                json_response = {"message": "Update not successful"}
                response = jsonify(json_response)
                response.status_code = 400
                return response
        else:
            # forward the request to the primary
            primary = node.coordinator
            url = node.neighbors[primary]
            endpoint = f"http://{url}:{CATALOG_PORT}/catalog/update" 

            response = requests.put(endpoint, json=json_request)
            if (response.status_code == 200):
                return response.json(), 200
            else:
                return response.json(), 500


class NodeInfo(Resource):
    '''
    Get the information and coordinator of the current system by a joining node
    '''
    def get(self):
        response = jsonify(
            {"node_id": node.node_id, "coordinator": node.coordinator, "neighbors": node.alive_neighbors})
        response.status_code = 200
        return response


class Election(Resource):
    '''
    Endpoint to start an election
    '''
    def post(self):
        data = request.get_json()
        node.alive_neighbors[int(data["node_id"])] = node.neighbors[int(data["node_id"])]

        if (data["node_id"] < node.node_id):
            higher_ids = {id_: url for id_, url in node.alive_neighbors.items() if int(id_) > node.node_id}
            if (len(higher_ids) > 0):
                t = threading.Thread(target=node.re_election)
                t.start()
                t.join()
            else:                
                t = threading.Thread(target=push_data)
                t.start()
                t.join()
        response = jsonify({'Response': 'OK'})
        response.status_code = 200
        return response


class Coordinator(Resource):
    def post(self):
        '''
        Receive the data the current primary
        Sync the data
        '''
        data = request.get_json()
        node.coordinator = data["coordinator"]
        books = data.get('Books', None)

        if books is not None:
            for serverBook in books:
                myBook = session.query(Book).filter_by(id=serverBook["id"]).one()
                if (myBook.cost != serverBook["cost"]):
                    myBook.cost = serverBook["cost"]

                if (myBook.stock != serverBook["stock"]):
                    myBook.stock = serverBook["stock"]

        response = jsonify({'Response': 'OK'})
        response.status_code = 200
        return response


class SyncDatabase(Resource):
    '''
    Called by a joining higher processID node to sync the database 
    with the current primary before starting the election
    '''
    def get(self):
        books = session.query(Book).all()
        data = {"Books": [book.serializeAll for book in books]}
        return data
