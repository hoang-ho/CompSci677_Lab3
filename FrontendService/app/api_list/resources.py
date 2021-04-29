from flask import request
from flask_restful import Resource
from sys import stdout
import threading

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
# Import config variables Default to backer server for consistency implementation for now. You'd need to modify this!
ORDER_HOST_1 = os.getenv('ORDER_HOST_1')
ORDER_HOST_2 = os.getenv('ORDER_HOST_2')
ORDER_PORT = os.getenv('ORDER_PORT')

# List of available Catalog Hosts and Order Hosts 
CATALOG_HOSTS = [CATALOG_HOST_1, CATALOG_HOST_2]
ORDER_HOSTS = [ORDER_HOST_1, ORDER_HOST_2]

#locks
search_lock = threading.Lock()
lookup_lock = threading.Lock()
buy_lock = threading.Lock()

# Local caching
cache = dict()

def choose_host(AVAILABLE_HOSTS, PORT, data, url):
    for HOST in AVAILABLE_HOSTS:
        logger.info(f'Trying HOST........ {HOST} at PORT........... {PORT}')
        try:
            heartbeat_resp = requests.get(f'http://{HOST}:{PORT}/healthcheck')
            if heartbeat_resp.status_code == 200:
                response = requests.get(f'http://{HOST}:{PORT}{url}', json=data)
            if response.status_code == 200:
                return response
        except:
            logger.info(f'server not available at {HOST}')


def choose_host_for_buy(AVAILABLE_HOSTS, PORT, data, url):
    for HOST in AVAILABLE_HOSTS:
        logger.info(f'Trying HOST........ {HOST} at PORT........... {PORT}')
        try:
            heartbeat_resp = requests.get(f'http://{HOST}:{PORT}/healthcheck')
            if heartbeat_resp.status_code == 200:
                response = requests.put(f'http://{HOST}:{PORT}{url}', json=data)
            if response.status_code == 200:
                return response
        except:
            logger.info(f'server not available at {HOST}')


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

            if target_key not in cache:
                response = ''
                search_lock.acquire()
                Search.search_count+=1
                search_lock.release()

                catalog_host_index = Search.search_count%2
                CATALOG_HOSTS_AVAILABLE = CATALOG_HOSTS[:catalog_host_index] + CATALOG_HOSTS[catalog_host_index+1:]               

                CATALOG_HOST = CATALOG_HOSTS[catalog_host_index]

                try:
                    heartbeat_resp = requests.get(f'http://{CATALOG_HOST}:{CATALOG_PORT}/healthcheck')
                    logger.info(f'Heartbeat check: {heartbeat_resp}')
                    if heartbeat_resp.status_code == 200:
                        response = requests.get(f'http://{CATALOG_HOST}:{CATALOG_PORT}/catalog/query', json=data)
                except:
                    logger.info(f'server not available at {CATALOG_HOST}')
                else:
                    self.t_end = time.time()
                    logger.info(f'execution time for search: {self.t_end-self.t_start}')
                    cache[target_key] = response.json()

                if not cache.get(target_key, None):
                    url = '/catalog/query'
                    response = choose_host(CATALOG_HOSTS_AVAILABLE, CATALOG_PORT, data, url)
                    self.t_end = time.time()
                    logger.info(f'execution time for search: {self.t_end-self.t_start}')
                    cache[target_key] = response.json()
            
            cached_response = cache[target_key]

            self.t_end = time.time()
            logger.info(f'execution time for search: {self.t_end-self.t_start}')
            return cached_response
        except:
            self.t_end = time.time()
            logger.info(f'execution time for lookup: {self.t_end-self.t_start}')
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

            if target_key not in cache:
                lookup_lock.acquire()
                LookUp.lookup_count+=1
                lookup_lock.release()

                catalog_host_index = LookUp.lookup_count%2
                CATALOG_HOSTS_AVAILABLE = CATALOG_HOSTS[:catalog_host_index] + CATALOG_HOSTS[catalog_host_index+1:]               

                CATALOG_HOST = CATALOG_HOSTS[catalog_host_index]

                try:
                    heartbeat_resp = requests.get(f'http://{CATALOG_HOST}:{CATALOG_PORT}/healthcheck')
                    logger.info(f'Heart beat: {heartbeat_resp}')
                    if heartbeat_resp.status_code == 200:
                        response = requests.get(f'http://{CATALOG_HOST}:{CATALOG_PORT}/catalog/query', json=data)
                except:
                    logger.info(f'server not available at {CATALOG_HOST}')
                else:
                    if response.status_code == 200:
                        self.t_end = time.time()
                        logger.info(f'execution time for search: {self.t_end-self.t_start}')
                        cache[target_key] = response.json()

                if not cache.get(target_key, None):
                    url = '/catalog/query'
                    response = choose_host(CATALOG_HOSTS_AVAILABLE, CATALOG_PORT, data, url)
                    self.t_end = time.time()
                    logger.info(f'execution time for lookup: {self.t_end-self.t_start}')
                    cache[target_key] = response.json()

            cached_response = cache[target_key]

            self.t_end = time.time()
            logger.info(f'execution time for search: {self.t_end-self.t_start}')
            return cached_response
        except:
            self.t_end = time.time()
            logger.info(f'execution time for lookup: {self.t_end-self.t_start}')
            return {'message': 'something went wrong. Please try again'}, 500
        

class Buy(Resource):
    '''
    Handle buy by id request
    '''
    buy_count=0
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

        data = {"id": id,'request_id':'Na'}

        # requesting to order
        try:
            buy_lock.acquire()
            Buy.buy_count+=1
            data['request_id']=Buy.buy_count
            buy_lock.release()
            order_host_index = Buy.buy_count % 2
            ORDER_HOSTS_AVAILABLE = ORDER_HOSTS[:order_host_index] + ORDER_HOSTS[order_host_index+1:]               

            ORDER_HOST = ORDER_HOSTS[order_host_index]

            try:
                heatbeat_resp = requests.get(f'http://{ORDER_HOST}:{ORDER_PORT}/healthcheck')
                if heatbeat_resp.status_code == 200:
                    response = requests.put(f'http://{ORDER_HOST}:{ORDER_PORT}/order', json=data)
            except:
                logger.info(f'server not available at {ORDER_HOST}')
            else:
                if response.status_code == 200:
                    self.t_end = time.time()
                    logger.info(f'execution time for search: {self.t_end-self.t_start}')
                    response_json = response.json()
                    book = response_json.get('book', '')
                    if(book):
                        return {'message': f'successfully purchased the book {book}'}
                    return response.json()

            url = '/order'
            response = choose_host_for_buy(ORDER_HOSTS_AVAILABLE, ORDER_PORT, data, url)
            self.t_end = time.time()
            logger.info(f'execution time for buy: {self.t_end-self.t_start}')
            response_json = response.json()
            book = response_json.get('book', '')
            if(book):
                return {'message': f'successfully purchased the book {book}'}
            return response.json()
        except:
            self.t_end = time.time()
            logger.info(f'execution time for lookup: {self.t_end-self.t_start}')
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
