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

CATALOG_PORT = os.getenv("CATALOG_PORT")
logger = logging.getLogger("Catalog-Service")

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
        self.neighbors = {all_ids[i]: all_urls[i] for i in range(len(all_ids))}
        self.url = self.neighbors[self.node_id]
        self.state = "STARTING"
        # self.alive_neighbors = {all_ids[i]: all_urls[i] for i in range(len(all_ids))}
        self.alive_neighbors = {self.node_id: self.url}
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
        # data = {"coordinator": self.node_id}

        logger.info(f'++++++++++++++++++++ data sending in annouce: {data}')

        for id_, url in self.neighbors.items():
            endpoint = f"http://{url}:{CATALOG_PORT}/coordinator"
            try:
                response = requests.post(endpoint, json=data, timeout=3.05)
            except requests.Timeout:
                response = None

            if (response and response.status_code == 200):
                logger.info("Done notifying node %d" % id_)
            else:
                logger.info("Could not notify node %d" % id_)
    
    def ping_primary(self):
        '''
        For the backup to ping the leader to check if the leader is alive
        If the leader dies, we begin a new election by return True
        '''
        # For those in the RUNNING system (with an appointed leader) to check if their leader is still alive
        url = self.neighbors[self.coordinator]
        endpoint = f"http://{url}:{CATALOG_PORT}/info"
        logger.info("Sending request to coordinator at " + endpoint)

        try:
            response = requests.get(endpoint, timeout=3.05)
        except requests.Timeout:
            response = None

        # if our coordinator is alive
        if (response and response.status_code == 200):
            # update our alive neighbors
            response_json = response.json()
            self.alive_neighbors = response_json.get("neighbors")
            return False
        else:
            self.alive_neighbors.pop(self.coordinator)
            # If leader dies, we return True to begin a new election
            return True

    def ready_for_election(self):
        '''
        This is for a STARTING node to check if it can begin an election
        Cases:
            - If there is already a RUNNING system, then this returns False so the STARTING node need to wait to join
            - If everyone is in STARTING state, then this returns True so we can begin an election
        '''
        executors = concurrent.futures.ThreadPoolExecutor(
            max_workers=len(list(self.alive_neighbors.keys())))
        # responses = []
        response = ()
        
        for id_, url in self.alive_neighbors.items():
            if (id_ != self.node_id):
                endpoint = f"http://{url}:{CATALOG_PORT}/info"
                logger.info("Sending request to node at " + endpoint)
                r = executors.submit(requests.get, endpoint, timeout=3.05)
                response = (r, id_)
                break
        
        coordinator = response[0].result()["coordinator"]
        
        # compare ID with the leader
        if (self.node_id > coordinator):
            # sync database and announce leadership
            url = self.alive_neighbors[coordinator]
            endpoint = f"http://{url}:{CATALOG_PORT}/sync_database"
            logger.info("Sending request to coordinator at " + endpoint)
        else:
            # sync database
            url = self.alive_neighbors[coordinator]
            endpoint = f"http://{url}:{CATALOG_PORT}/election"
            response = requests.post(endpoint, timeout=3.05)
    
    def ping_backups(self):
        '''
        For the primary to ping backups to check if the node is still alive
        '''
        if (self.node_id == self.coordinator):
            executors = concurrent.futures.ThreadPoolExecutor(max_workers=len(list(self.alive_neighbors.keys())))
            responses = []
            for id_, url in self.alive_neighbors.items():
                if (id_ != self.node_id):
                    endpoint = f"http://{url}:{CATALOG_PORT}/info"
                    logger.info("Sending request to node at " + endpoint)
                    r = executors.submit(requests.get, endpoint, timeout=3.05)
                    responses.append((r, id_))
            
            for r, id_ in responses:
                if r.result().status_code != 200:
                    self.alive_neighbors.pop(id_)
    
    def get_alive_neighbors(self):
        '''
        This checks is performed by a node that is in starting state - 
        to get a list of all the other alive nodes in the systems
        '''
        executors = concurrent.futures.ThreadPoolExecutor(max_workers=len(list(self.alive_neighbors.keys())))
        responses = []
        
        for id_, url in self.neighbors.items():
            if (id_ != self.node_id):
                endpoint = f"http://{url}:{CATALOG_PORT}/healthcheck"
                logger.info("Sending request to node at " + endpoint)
                r = executors.submit(requests.get, endpoint, timeout=3.05)
                responses.append((r, id_))
        
        for r, id_ in responses:
            if r.result().status_code == 200:
                self.alive_neighbors.add(id_, self.neighbors[id_])
                # response_json = r.result().json()
                # if (self.node_id not in response_json.get("neighbors")):
                #     return False

        return True
        

def BeginElection(node, wait=True):

    # get all alive neighbors
    node.get_alive_neighbors()

    logger.info(f'============= len of alive neighbors: {len(node.alive_neighbors)}')

    if len(node.alive_neighbors) == 1:
        # This means that there is only one node and they are the leader
        # We will have to annouce that the node is a coordinator
        node.announce()
    else:
        # Handle new node entering the system scenario
        node.ready_for_election()
            
        # if there is already a running system, we wait
        while(True):
            if (node.coordinator == node.node_id):
                node.ping_backups()
            else:
                node.ping_primary()
            
            time.sleep(3)