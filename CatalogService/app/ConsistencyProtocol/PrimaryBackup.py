import os
import requests
import logging
from sys import stdout
import time
import random
import threading
import concurrent.futures
import json
from utils import synchronized

# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker
# from sqlalchemy.pool import StaticPool
from database.database_setup import Base, Book, session

CATALOG_PORT = os.getenv("CATALOG_PORT")
logger = logging.getLogger("Catalog-Service")

# Connect to Database and create database session
# engine = create_engine('sqlite:///books-collection.db',
#                        echo=True, connect_args={'check_same_thread': False})

# Base.metadata.bind = engine

# DBSession = sessionmaker(bind=engine)
# session = DBSession()

class Node:

    def __init__(self, coordinator=-1):
        '''
        node_id: id of the node
        neighbors: id to url map for all nodes in the system
        coordinator: id of the coordinator
        '''
        self.node_id = int(os.getenv("PROCESS_ID"))
        all_ids = [int(val) for val in os.getenv("ALL_IDS").split(",")]
        all_urls = [val for val in os.getenv("ALL_HOSTNAMES").split(",")]
        self.neighbors = {all_ids[i]: all_urls[i] for i in range(len(all_ids)) if all_ids[i] != self.node_id}
        self.alive_neighbors = {}
        self.coordinator = coordinator
        self.lock = threading.Lock()        
    
    def election(self):
        '''
        To send ELECTION message to node with higher ids
        '''
        higher_ids = {id_: url for id_,
                      url in self.alive_neighbors.items() if id_ > self.node_id}

        data = {"node_id": self.node_id}
        response_codes = []

        for id_, url in higher_ids.items():
            endpoint = f"http://{url}:{CATALOG_PORT}/election"
            try:
                response = requests.post(endpoint, json=data, timeout = 3.05)
                response_codes.append(response.status_code)
            except requests.Timeout:
                response_codes.append(500)

        if 200 in response_codes:
            return True
        else:
            return False
    
    def announce(self, data={}):
        '''
        To send COORDINATOR message to node with lower ids
        '''
        self.coordinator = self.node_id
        data["coordinator"] = self.node_id

        logger.info(f'++++++++++++++++++++ data sending in annouce: {data}')

        for id_, url in self.neighbors.items():
            endpoint = f"http://{url}:{CATALOG_PORT}/coordinator"
            try:
                response = requests.post(endpoint, json=data, timeout=3.05)
            except:
                response = None

            if (response and response.status_code == 200):
                logger.info("Done notifying node %d" % id_)
            else:
                logger.info("Could not notify node %d" % id_)

    def ready_for_election(self):
        '''
        This is for a STARTING node to check if it can begin an election
        Cases:
            - If there is already a RUNNING system, then this returns False so the STARTING node need to wait to join
            - If everyone is in STARTING state, then this returns True so we can begin an election
        '''
        executors = concurrent.futures.ThreadPoolExecutor(max_workers=len(list(self.neighbors.keys())))
        # responses = []
        # response
        
        for id_, url in self.alive_neighbors.items():
            if (id_ != self.node_id):
                endpoint = f"http://{url}:{CATALOG_PORT}/info"
                logger.info("Sending request to node at " + endpoint)
                r = executors.submit(wrapper_get_request,endpoint)
                response = r
                break
        
        logger.info(f'+++++++++++++ in ready for election: {response}')
        coordinator = response.result().json()["coordinator"]
        
        # compare ID with the leader
        if (self.node_id > coordinator):
            # sync database and announce leadership
            url = self.alive_neighbors[coordinator]
            logger.info(f'+++++++++++++ starting syncing contaction: {url}')
            # self.lock.acquire()
            # books = session.query(Book).all()
            # data = {"Books": [book.serializeAll for book in books]}
            # logger.info(f"Sending data {data}")
            # node.announce(json_data)
            endpoint = f"http://{url}:{CATALOG_PORT}/sync_database"
            logger.info("Sending request to coordinator at " + endpoint)
            response = requests.get(endpoint, timeout=3.05)
            json_response = response.json()
            logger.info(f"Data received {json_response}")
            self.lock.acquire()
            for serverBook in json_response["Books"]:
                myBook = session.query(Book).filter_by(id=serverBook["id"]).one()
                if (myBook.cost != serverBook["cost"]):
                    myBook.cost = serverBook["cost"]
                
                if (myBook.stock != serverBook["stock"]):
                    myBook.stock = serverBook["stock"]
            self.lock.release()
            # initialize the election
            higher_ids = {id_: url for id_, url in self.alive_neighbors.items() if id_ > self.node_id}
            if (len(higher_ids) == 0):
                # announce
                # node.state = "RUNNING"
                self.announce()
            else:
                self.election()
        else:
            # sync database
            url = self.alive_neighbors[coordinator]
            endpoint = f"http://{url}:{CATALOG_PORT}/election"
            data = {"node_id": self.node_id}
            logger.info("Sending request to coordinator at " + endpoint)
            response = requests.post(endpoint, json=data, timeout=3.05)
            logger.info(f"Response from coordinator at {response.status_code}")
     
    def get_alive_neighbors(self):
        '''
        This checks is performed by a node that is in starting state - 
        to get a list of all the other alive nodes in the systems
        '''
        executors = concurrent.futures.ThreadPoolExecutor(max_workers=len(list(self.neighbors.keys())))
        responses = []
        
        for id_, url in self.neighbors.items():
            if (id_ != self.node_id):
                endpoint = f"http://{url}:{CATALOG_PORT}/healthcheck"
                logger.info("Sending request to node at " + endpoint)
                r = executors.submit(wrapper_get_request, endpoint)
                responses.append((r, id_))
        
        for r, id_ in responses:
            logger.info(f'in get_alive_neighbors: {r}')
            if r.result() is not None:
                self.alive_neighbors[id_] = self.neighbors[id_]
                # self.alive_neighbors.add(id_, self.neighbors[id_])
    
    def ping_backups(self):
        '''
        For the primary to ping backups to check if the node is still alive
        '''
        if (self.node_id == self.coordinator):

            executors = concurrent.futures.ThreadPoolExecutor(
                max_workers=len(list(self.neighbors.keys())))
            responses = []

            for id_, url in self.alive_neighbors.items():
                if (id_ != self.node_id):
                    endpoint = f"http://{url}:{CATALOG_PORT}/info"
                    logger.info("Sending request to node at " + endpoint)
                    r = executors.submit(wrapper_get_request, endpoint)
                    responses.append((r, id_))

            for r, id_ in responses:
                logger.info(f'in ping backups: {r}')
                if r.result() is not None:
                    self.alive_neighbors.pop(id_)
    
    def ping_primary(self):
        '''
        For the backup to ping the leader to check if the leader is alive
        If the leader dies, we begin a new election by return True
        '''
        # For those in the RUNNING system (with an appointed leader) to check if their leader is still alive
        if (self.coordinator == -1):
            # Wait a bit for the coordinator endpoint to return
            return

        url = self.neighbors[self.coordinator]
        endpoint = f"http://{url}:{CATALOG_PORT}/info"
        logger.info("Sending request to coordinator at " + endpoint)
        response = None

        try:
            response = requests.get(endpoint, timeout=3.05)
        except requests.Timeout:
            response = None

        logger.info(f'------------ in ping primary response: {response}')
        # if our coordinator is alive
        if (response and response.status_code == 200):
            # update our alive neighbors
            response_json = response.json()
            self.alive_neighbors = response_json.get("neighbors")
            return False
        else:
            self.alive_neighbors.pop(self.coordinator)
            self.coordinator = -1
            self.re_election()
            # If leader dies, we return True to begin a new election
            return True

    def re_election(self):
        if len(node.alive_neighbors) == 0:
            node.announce()
        else:
            for id_, url in self.alive_neighbors.items():
                if (id_ != self.node_id):
                    endpoint = f"http://{url}:{CATALOG_PORT}/election"
                    data = {"node_id": self.node_id}
                    logger.info("Sending request to coordinator at " + endpoint)
                    response = requests.post(endpoint, json=data, timeout=3.05)
                    logger.info(f"Response from coordinator at {response.status_code}")


def wrapper_get_request(endpoint):
    try:
        response = requests.get(endpoint, timeout=3.05)
        if response.status_code == 200:
            return response
        else:
            return None
    except:
        logger.info(f'Node not alive at: {endpoint}')
    
    return None


def BeginElection(node, wait=True):

    logger.info(f'============= before len of alive neighbors: {len(node.alive_neighbors)}')

    # get all alive neighbors
    node.get_alive_neighbors()

    logger.info(f'============= len of alive neighbors: {len(node.alive_neighbors)}')

    if len(node.alive_neighbors) == 0:
        # This means that there is only one node and they are the leader
        # We will have to annouce that the node is a coordinator
        node.announce()
    else:
        # Handle new node entering the system scenario
        node.ready_for_election()
        
    # if there is already a running system, we wait
    while(True):
        if (node.coordinator != node.node_id):

            # node.ping_backups()
        #     pass
        # else:

            ping_response = node.ping_primary()
            time.sleep(3)
        #     if response:
        # del node.alive_neighbors[node.coordinator]
        # node.coordinator = -1
        # node.re_election()

        
