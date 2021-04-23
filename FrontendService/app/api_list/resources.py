from flask import request
from flask_restful import Resource
from sys import stdout

import logging
import os
import requests
import time


# Define logging
logger = logging.getLogger('front-end-service')

logger.setLevel(logging.INFO) # set logger level
logFormatter = logging.Formatter\
("%(name)-12s %(asctime)s %(levelname)-8s %(filename)s:%(funcName)s %(message)s")
consoleHandler = logging.StreamHandler(stdout) #set streamhandler to stdout
consoleHandler.setFormatter(logFormatter)
logger.addHandler(consoleHandler)


# Import config variables Default to backer server for consistency implementation for now. You'd need to modify this!
CATALOG_HOST_1 = os.getenv('CATALOG_HOST_1')
CATALOG_HOST_2 = os.getenv('CATALOG_HOST_2')
CATALOG_PORT = os.getenv('CATALOG_PORT')
ORDER_HOST = os.getenv('ORDER_HOST')
ORDER_PORT = os.getenv('ORDER_PORT')


# Local caching
cache = dict()


class Search(Resource):
    '''
    Handle search by topic request
    '''
    search_count=0
    t_start = time.time()
    t_end = 0
    def get(self, topic_name=None):
        # return the expected value
        if not topic_name:
            return {
                'Operation': 'GET',
                'URL': '<address>:<port>/search/<topic_name>',
                'topic_name': 'a string of the value distributed-systems or graduate-school'
            }

        # validation
        if(topic_name == 'distributed-systems'):
            data = {"topic": "distributed systems"}
        elif(topic_name == 'graduate-school'):
           data = {"topic": "graduate school"}
        else:
            self.t_end = time.time()
            logger.info(f'execution time for search: {self.t_end-self.t_start}')
            return {"message": "topic name should be in [distributed-systems, graduate-school]"}, 400     
        
        # requesting to catalog
        try:
            target_key = f'search-{topic_name}'
            logger.info(f'target key: {target_key}')
            if target_key not in cache:
                Search.search_count+=1
                logger.info(f'calling the backend server')
                if Search.search_count%2==0:
                    response = requests.get(f'http://{CATALOG_HOST_1}:{CATALOG_PORT}/catalog/query', json=data)
                else:
                    response = requests.get(f'http://{CATALOG_HOST_2}:{CATALOG_PORT}/catalog/query', json=data)

                if response.status_code == 200:
                    self.t_end = time.time()
                    logger.info(f'execution time for search: {self.t_end-self.t_start}')
                    cache[target_key] = response.json()
            
            cached_response = cache[target_key]
            logger.info(f'returning cached response')
            self.t_end = time.time()
            logger.info(f'execution time for search: {self.t_end-self.t_start}')
            return cached_response, 200
        except:
            self.t_end = time.time()
            logger.info(f'execution time for search: {self.t_end-self.t_start}')
            return {'message': 'something went wrong. Please try again'}, 500


class LookUp(Resource):
    '''
    Handle look by id request
    '''
    lookup_count = 0
    t_start = time.time()
    t_end = 0
    def get(self, item_id=None):
        # return the expected value
        if not item_id:
            return {
                'Operation': 'GET',
                'URL': '<address>:<port>/lookup/<item_id>',
                'item_id': 'string that specifies the book id. It accepts value from 1 to 4'
            }

        # validation
        id = int(item_id)
        if(id > 4 or id < 1):
            self.t_end = time.time()
            logger.info(f'execution time for lookup: {self.t_end-self.t_start}')
            return {"message": "Please enter a correct id"}, 400  

        data = {"id": id}

        # requesting to catalog
        try:
            target_key = f'lookup-{item_id}'
            logger.info(f'target key: {target_key}')
            if target_key not in cache:
                logger.info(f'calling the backend server')
                LookUp.lookup_count+=1
                if LookUp.lookup_count%2==0:
                    response = requests.get(f'http://{CATALOG_HOST_1}:{CATALOG_PORT}/catalog/query', json=data)
                else:
                    response = requests.get(f'http://{CATALOG_HOST_2}:{CATALOG_PORT}/catalog/query', json=data)
                if response.status_code == 200:
                    self.t_end = time.time()
                    logger.info(f'execution time for lookup: {self.t_end-self.t_start}')
                    cache[target_key] = response.json()

            cached_response = cache[target_key]
            logger.info(f'returning cached response')
            self.t_end = time.time()
            logger.info(f'execution time for search: {self.t_end-self.t_start}')
            return cached_response, 200
        except:
            self.t_end = time.time()
            logger.info(f'execution time for lookup: {self.t_end-self.t_start}')
            return {'message': 'something went wrong. Please try again'}, 500
        

class Buy(Resource):
    '''
    Handle buy by id request
    '''

    t_start = time.time()
    t_end = 0
    def post(self, item_id=None):
        # return the expected value
        if not item_id:
            return {
                'Operation': 'POST',
                'URL': '<address>:<port>/buy/<item_id>',
                'topic_name': 'string that specifies the book id. It accepts value from 1 to 4'
            }

        # validation
        id = int(item_id)
        if(id > 4 or id < 1):
            self.t_end = time.time()
            logger.info(f'execution time for buy: {self.t_end-self.t_start}')
            return {"message": "Please enter a correct id"}, 400  

        data = {"id": id}

        # requesting to order
        try:
            response = requests.put(f'http://{ORDER_HOST}:{ORDER_PORT}/order', json=data)
            if response.status_code == 200:
                self.t_end = time.time()
                logger.info(f'execution time for buy: {self.t_end-self.t_start}')
                response_json = response.json()
                book = response_json.get('book', '')
                if(book):
                    return {'message': f'successfully purchased the book {book}'}
                return response.json()
        except:
            self.t_end = time.time()
            logger.info(f'execution time for buy: {self.t_end-self.t_start}')
            return {'message': 'something went wrong. Please try again'}, 500


class Cache(Resource):
    '''
    Endpoint to invalidate cache
    '''

    def post(self):
        data = request.json
        logger.info(f'request data: {data}')

        # If topic name or id of the book has been updated
        if(data.get('topic_name')):
            logger.info(f'In id data cache: {cache}')
            target_key = f'lookup-{data["topic_name"]}'
            logger.info(f'target key to pop: {target_key}')
            invalidate = cache.pop(target_key, None)

        # If stock and cost has been updated
        if(data.get('id')):
            logger.info(f'In id data cache: {cache}')
            target_key = f'lookup-{data["id"]}'
            logger.info(f'target key to pop: {target_key}')
            invalidate = cache.pop(target_key, None)

        # logger.info(f'Invalidate the entry: {invalidate}')
