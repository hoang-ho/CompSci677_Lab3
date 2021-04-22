from flask import request, jsonify
from flask_restful import Api, Resource
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from database.database_setup import Base, Book
from ConsistencyProtocol.BullyAlgorithm import Node, BeginElection
from utils import synchronized
from sys import stdout
import logging
import threading
import json
import time
import os
import requests


logger = logging.getLogger("Catalog-Service")

logger.setLevel(logging.INFO)  # set logger level
logFormatter = logging.Formatter(
    "%(name)-12s %(asctime)s %(levelname)-8s %(filename)s:%(funcName)s %(message)s")
consoleHandler = logging.StreamHandler(stdout)  # set streamhandler to stdout
consoleHandler.setFormatter(logFormatter)
logger.addHandler(consoleHandler)

# Connect to Database and create database session
engine = create_engine('sqlite:///books-collection.db',
                       echo=True, connect_args={'check_same_thread': False})

Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()
node = Node(int(os.getenv("REPLICA_ID")))
lock = threading.Lock()


@synchronized
def log_request(newData, key):
    '''
    Write requests to a logfile in case the the database or the app goes down. We can reconstruct from this log file
    '''
    fd = open('logfile.json', "r+")
    data = json.loads(fd.read())
    data[key].append(newData)
    fd.seek(0)
    json.dump(data, fd)
    fd.truncate()
    fd.close()


@synchronized
def update_data(json_request):
    '''
    json_request: a request of type json that contains id to query book by id and update/buy the book
    This is a synchronized function
    '''
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


def prepopulate():
    logger.info("Prepopulate data")
    if (session.query(Book).first() is None):
        f = open('logfile.json', "r")
        data = json.loads(f.read())

        # add all the book
        for book in data["add"]:
            session.add(Book(
                title=book["title"], topic=book["topic"], stock=book["stock"], cost=book["cost"]))
        session.commit()

        # update according to timestamp
        if (data["update"]):
            update = sorted(data["update"], key=lambda k: k["timestamp"])
            for book in update:
                session.query(Book).filter_by(
                    id=book["id"]).update({"stock": book["stock"], "cost": book["cost"]})
            session.commit()

class Ping(Resource):
    def get(self):
        response = jsonify({'Response': 'OK'})
        response.status_code = 200
        return response

class Query(Resource):
    def get(self):
        '''
        Handle get request for search by topic and lookup by id
        '''
        books = []
        request_data = request.get_json()
        logger.info("Receive a query request ")
        if (request_data and ("id" in request_data or "topic" in request_data)):
            if ("id" in request_data):
                books = session.query(Book).filter_by(
                    id=request_data["id"]).all()
                if (len(books) == 0):
                    response = jsonify(success=False)
                    response.status_code = 400
                else:
                    logRequest = {
                        "id": request_data["id"], "timestamp": time.time()}
                    log_request(logRequest, "query")
                    response = jsonify(books[0].serializeQueryById)
                    response.status_code = 200

            elif ("topic" in request_data):
                books = session.query(Book).filter_by(
                    topic=request_data["topic"]).all()
                logRequest = {
                    "topic": request_data["topic"], "timestamp": time.time()}
                log_request(logRequest, "query")
                response = jsonify(
                    items={book.title: book.id for book in books})
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
        logger.info("Receive a buy request")
        json_request = request.get_json()

        # forward request to primary
        if (node.node_id != node.coordinator):
            pass
        else:
            if ("id" in json_request):
                json_request["buy"] = True
                title = update_data(json_request)
                
                # concurrently update data in other replicas

                logger.info("Update data for book " + title)
                response = jsonify(book=title)
                response.status_code = 200
            else:
                response = jsonify(success=False)
                response.status_code = 400
        return response


class Update(Resource):
    def put(self):
        '''
        Handle put request for update
        Return 200 if update succeeds
        '''
        logger.info("Receive an update request")
        json_request = request.get_json()

        if (json_request and "id" in json_request):
            json_request["buy"] = False
            title = update_data(json_request)
            logger.info("Update data for book " + title)
            json_response = {"message": "Done update", "book": title}
            response = jsonify(json_response)
            response.status_code = 200
            return response
        else:
            json_response = {"message": "Update not successful"}
            response = jsonify(json_response)
            response.status_code = 400
            return response


class NodeInfo(Resource):
    def get(self):
        response = jsonify(
            {"node_id": node.node_id, "coordinator": node.coordinator})
        response.status_code = 200
        return response

class Election(Resource):
    counter = 0
    def post(self):
        lock.acquire()
        Election.counter += 1
        lock.release()

        data = request.get_json()
        if (Election.counter == 1 and data["node_id"] < node.node_id):
            # Open up a thread to begin the Election
            threading.Thread(target=BeginElection, args=(node, False)).start()
        response = jsonify({'Response': 'OK'})
        response.status_code = 200
        return response

class Coordinator(Resource):
    def post(self):
        data = request.get_json()
        node.coordinator = data["coordinator"]
        logger.info("Setting Coordinator as %d in node %d" % (node.coordinator, node.node_id))
        response = jsonify({'Response': 'OK'})
        response.status_code = 200
        return response
