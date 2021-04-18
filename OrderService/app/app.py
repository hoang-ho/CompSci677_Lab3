#coding: utf-8

from flask import Flask, request, jsonify
from flask_restful import Resource, Api
import json
import requests
app = Flask(__name__)
api = Api(app)
import sqlite3 as sql
from datetime import datetime
import os
import threading


# Import config variables
CATALOG_HOST = os.getenv('CATALOG_HOST')
CATALOG_PORT = os.getenv('CATALOG_PORT')


@app.before_first_request
def init_database():
    conn = sql.connect('database.db')
    conn.execute('CREATE TABLE IF NOT EXISTS buy_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, request_id INTEGER NOT NULL, timestamp TEXT NOT NULL)')
    conn.close()


class LogService(Resource):
    def get(self):
        with sql.connect("database.db") as conn:
            conn.row_factory = sql.Row
            cur = conn.cursor()
            cur.execute("select * from buy_logs")
            rows = cur.fetchall()
            row_list=[]
            for row in rows:
                row_list.append({'id':row['id'],'request_id':row['request_id'],'timestamp':row['timestamp']})
        if rows:
            result=json.dumps(row_list)
        else:
            result=json.dumps( {'message': 'Log is empty'})
        return result

class OrderService(Resource):

    def put(self):
        '''
        Handle a put request to buy a book
        '''
        request_data = request.get_json()
        id= request_data['id']
        if not id:
            return json.dumps({'message':"Invalid request"})

        with sql.connect("database.db") as conn:
             cur = conn.cursor()
             time_stamp = str(datetime.now())
             cur.execute("INSERT INTO buy_logs (request_id,timestamp) VALUES( ?, ?)",  (id,time_stamp ))
             conn.commit()
        response = requests.get(f"http://{CATALOG_HOST}:{CATALOG_PORT}/catalog/query", json={"id": id})
        response_json = response.json()
        if response.status_code!=200:
            return {'message': "Error in receiving response from catalog service"}, 500
        
        quantity = response_json['stock']
        if quantity > 0:
            response = requests.put(f"http://{CATALOG_HOST}:{CATALOG_PORT}/catalog/buy", json={"id": id})
            if response.status_code == 200:
                return response.json(), 200
            else:
                return {'message': 'Buy request falied'}, 500
        else:
            return {'message': 'Item not available'}, 200

        return {'message': 'Error while buying'}, 500

api.add_resource(OrderService, "/order")
api.add_resource(LogService, "/log")


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0',threaded=True ,port=5007)

