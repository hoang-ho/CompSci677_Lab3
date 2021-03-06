from flask import Flask, request, jsonify
from flask_restful import Resource, Api
from sys import stdout
import json
import requests

app = Flask(__name__)
api = Api(app)

import sqlite3 as sql
from datetime import datetime
import os
import logging
import threading

# Define logging
logger = logging.getLogger('front-end-service')

logger.setLevel(logging.INFO) # set logger level
logFormatter = logging.Formatter\
("%(name)-12s %(asctime)s %(levelname)-8s %(filename)s:%(funcName)s %(message)s")
consoleHandler = logging.StreamHandler(stdout) #set streamhandler to stdout
consoleHandler.setFormatter(logFormatter)
logger.addHandler(consoleHandler)

CATALOG_HOST = os.getenv('CATALOG_HOST')
CATALOG_PORT = os.getenv('CATALOG_PORT')

@app.before_first_request
def init_database():
    conn = sql.connect('database.db')
    conn.execute('CREATE TABLE IF NOT EXISTS buy_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, request_id INTEGER NOT NULL, timestamp TEXT NOT NULL,query_id TEXT NOT NULL)')
    conn.close()


class HealthCheck(Resource):
    '''
    Endpoint to check if the node is running
    '''
    def get(self):
        response = jsonify({'message': 'OK'})
        response.status_code = 200
        return response


class LogService(Resource):
    '''
    Endpoint to see the logging of each Order Service
    '''
    def get(self):
        with sql.connect("database.db") as conn:
            conn.row_factory = sql.Row
            cur = conn.cursor()
            cur.execute("select * from buy_logs")
            rows = cur.fetchall()
            row_list=[]
            for row in rows:
                row_list.append({'id':row['id'],'request_id':row['request_id'],'timestamp':row['timestamp'],'query_id':row['query_id']})
        if rows:
            result=json.dumps(row_list)
        else:
            result=json.dumps( {'message': 'Log is empty'})
        return result


class OrderService(Resource):
    order_count=0

    def put(self):
        '''
        Handle a put request to buy a book
        '''
        request_data = request.get_json()
        book_id = request_data['book_id']
        request_id = request_data['request_id']
        if not book_id:
            return json.dumps({'message':"Invalid request"})

        with sql.connect("database.db") as conn:
             cur = conn.cursor()
             time_stamp = str(datetime.now())
             cur.execute("INSERT INTO buy_logs (request_id, timestamp, query_id) VALUES( ?, ?,?)",  (request_id, time_stamp, book_id ))
             conn.commit()

        try:
            # checking if the book is in stock
            response = requests.get(f'http://{CATALOG_HOST}:{CATALOG_PORT}/catalog/query', json={'id': book_id})
            response_json = response.json()
            if response.status_code == 200:
                quantity = response_json['stock']
                if quantity > 0:
                    try:
                        # initiating buying request to the catalog server
                        response = requests.put(f'http://{CATALOG_HOST}:{CATALOG_PORT}/catalog/buy', json={'book_id': book_id, 'request_id':request_id})
                        if response.status_code == 200:
                            return response.json(), 200
                    except:
                        return {'message': 'Buy request falied'}, 500
                else:
                    return {'message': 'Item not available'}, 200
        except:
            return {'message': 'Catalog Service not running'}, 500


'''
API Endpoints for the Order Service
'''
api.add_resource(OrderService, "/order")
api.add_resource(LogService, "/log")
api.add_resource(HealthCheck, "/healthcheck")


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0',threaded=True ,port=5007)

