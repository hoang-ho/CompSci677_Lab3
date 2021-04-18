from flask import Flask, request, jsonify
from flask_restful import Api, Resource
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from database_setup import Base, Book
import threading
import json
import time

app = Flask(__name__)
api = Api(app)

# Connect to Database and create database session
engine = create_engine('sqlite:///books-collection.db',
                       echo=True, connect_args={'check_same_thread': False})

Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


def synchronized(func):
    '''
    synchronized decorator
    '''

    func.__lock__ = threading.Lock()

    def synced_func(*args, **kws):
        with func.__lock__:
            return func(*args, **kws)

    return synced_func

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


@app.before_first_request
def prepopulate():
    app.logger.info("Prepopulate data")
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
class Query(Resource):
    def get(self):
        '''
        Handle get request for search by topic and lookup by id
        '''
        books = []
        request_data = request.get_json()
        app.logger.info("Receive a query request ")
        if (request_data and ("id" in request_data or "topic" in request_data)):
            if ("id" in request_data):
                books = session.query(Book).filter_by(id=request_data["id"]).all()
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
        Handle put request for buy
        Return 200 if buy succeeds
        '''
        app.logger.info("Receive a buy request")
        json_request = request.get_json()
        if ("id" in json_request):
            json_request["buy"] = True
            title = update_data(json_request)
            app.logger.info("Update data for book " + title)
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
        app.logger.info("Receive an update request")
        json_request = request.get_json()

        if (json_request and "id" in json_request):
            json_request["buy"] = False
            title = update_data(json_request)
            app.logger.info("Update data for book " + title)
            json_response = {"message": "Done update", "book": title}
            response = jsonify(json_response)
            response.status_code = 200
            return response
        else:
            json_response = {"message": "Update not successful"}
            response = jsonify(json_response)
            response.status_code = 400
            return response

api.add_resource(Query, "/catalog/query")
api.add_resource(Buy, "/catalog/buy")
api.add_resource(Update, "/catalog/update")

if __name__ == "__main__":
    # run the application
    app.debug = True
    app.run(host='0.0.0.0', port=5002)
