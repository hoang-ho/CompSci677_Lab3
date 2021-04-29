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
        self.alive_neighbors = {all_ids[i]: all_urls[i] for i in range(len(all_ids))}
        self.coordinator = coordinator
    
    def election(self, higher_ids):
        '''
        To send ELECTION message to node with higher ids
        '''

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
    
    def announce(self):
        '''
        To send COORDINATOR message to node with lower ids
        '''
        self.coordinator = self.node_id
        data = {"coordinator": self.node_id}

        for id_, url in self.neighbors.items():
            endpoint = f"http://{url}:{CATALOG_PORT}/coordinator"
            try:
                response = requests.post(endpoint, json=data, timeout=3.05)

            if (response and response.status_code == 200):
                logger.info("Done notifying node %d" % id_)
            else:
                logger.info("Could not notify node %d" % id_)
     
    def ready_for_election(self):
        '''
        Check if we need a new election to appoint a new leader
        Cases when a new election is needed:
            If no leader has been appointed, every node has its coordinator value set to -1
            If leader dies, backups node haven't received the heartbeat from coordinator
            If a new node just joins the system, 
        '''
        # check if we have the leader appointed and the leader is alive
        if (self.coordinator != -1 and self.node_id != self.coordinator):
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
        
        # if we don't have the leader appointed,
        # then we either haven't received the announcement
        # or just join the system.
        # Thus we begin a new election
        return True
    
    def primary_ping(self):
        '''
        For the primary to ping everyone to check if the node is still alive
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
                if r.result.status_code != 200:
                    self.alive_neighbors.pop(id_)
    
    def check_in_network(self):
        '''
        This is to check if the node is in the system
        If it is not in the system, it need to sync with everyone first before joining the system
        '''
        executors = concurrent.futures.ThreadPoolExecutor(max_workers=len(list(self.alive_neighbors.keys())))
        responses = []
        for id_, url in self.alive_neighbors.items():
            if (id_ != self.node_id):
                endpoint = f"http://{url}:{CATALOG_PORT}/info"
                logger.info("Sending request to node at " + endpoint)
                r = executors.submit(requests.get, endpoint, timeout=3.05)
                responses.append((r, id_))
        
        for r, id_ in responses:
            if r.result.status_code == 200:
                response_json = r.json()
                if (self.node_id not in response_json.get("neighbors")):
                    return False
        
        return True
        

def BeginElection(node, wait=True):
    while node.check_in_network():
        # For recovery
        # First check if you are in everyone else network
        # How to know that? Ask everyone if you're their alive neighbors        

        # check if we have a leader and the leader is alive
        election_ready = node.ready_for_election(node.neighbors)
        logger.info("Election ready? " + str(election_ready))
        
        if election_ready:
            logger.info('Starting election in: %s' % node.node_id)
            higher_ids = {id_:url for id_, url in node.neighbors.items() if id_ > node.node_id}
            
            # we are the node with the highest id, announce ourselves as the coordinator
            if (len(higher_ids) == 0):
                logger.info("Announcing Coordinator as %d " % node.node_id)
                node.announce(node.neighbors)
            else: 
                # Send election message to node with higher id
                if node.election(higher_ids) == False:
                    # If none of the node with higher id is alive
                    # This node becomes the leader
                    node.announce(node.neighbors)

        # for primary to check if everyone is alive
        node.primary_ping()
        # sleep for 3 seconds before checking again!
        time.sleep(4)

def sync_data(node):
    '''
    For a newly joined node to sync data with the current system 
    '''
    # find who the current leader is
    coordinator = -1
    for id_, url in node.neighbors.items():
        endpoint = f"http://{url}:{CATALOG_PORT}/info"
        logger.info("Sending request to neighbor at " + endpoint)
        try:
            response = requests.get(endpoint, timeout=3.05)
        except requests.Timeout:
            response = None

        # if our coordinator is alive
        if (response and response.status_code == 200):
            coordinator = response["coordinator"]
        
        if coordinator != -1:
            break
    
    # sync with the coordinator
    if (coordinator != -1):
        url = node.neighbors[coordinator]
        endpoint = f"http://{url}:{CATALOG_PORT}/sync_database"
        logger.info("Sending request to neighbor at " + endpoint)
        try:
            response = requests.get(endpoint, timeout=3.05)
        except requests.Timeout:
            response = None

        if (response.status_code == 200):
            # Check if database is the same as the primary
            fd = open('base_database.json', "r+")
            data = json.loads(fd.read())

            # Compare
            for book in response["Books"]:
                key = "book_id_%s" % str(book["id"])
                if (data[key]["stock"] != book["stock"]):
                    data[key]["stock"] = book["stock"]
                if (data[key]["cost"] != book["cost"]):
                    data[key]["cost"] = book["cost"]
            fd.seek(0)
            json.dump(data, fd)
            fd.truncate()
            fd.close()
