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

from database.database_setup import Base, Book, session

CATALOG_PORT = os.getenv("CATALOG_PORT")
logger = logging.getLogger("Catalog-Service")


class Node:

    def __init__(self, coordinator=-1):
        '''
        node_id: id of the node
        neighbors: id to url map for all nodes in the system
        alive_neighbors: id to url map for all running nodes in the system
        coordinator: id of the coordinator
        '''
        self.node_id = int(os.getenv("PROCESS_ID"))
        all_ids = [int(val) for val in os.getenv("ALL_IDS").split(",")]
        all_urls = [val for val in os.getenv("ALL_HOSTNAMES").split(",")]
        self.neighbors = {int(all_ids[i]): all_urls[i] for i in range(len(all_ids)) if all_ids[i] != self.node_id}
        self.alive_neighbors = {}
        self.coordinator = coordinator
        self.lock = threading.Lock()        
    
    def election(self):
        '''
        To send ELECTION message to node with higher ids
        '''
        higher_ids = {id_: url for id_,url in self.alive_neighbors.items() if id_ > self.node_id}

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
        This is for a newly joining or recovering node to check if it can begin an election
        Cases:
            - If there is already a RUNNING system, then this returns False so the joining node needs to wait to join
            - If everyone is in STARTING state, then this returns True so we can begin an election
        '''
        executors = concurrent.futures.ThreadPoolExecutor(max_workers=len(list(self.neighbors.keys())))
        responses = []
        for id_, url in self.alive_neighbors.items():
            if (id_ != self.node_id):
                endpoint = f"http://{url}:{CATALOG_PORT}/info"
                r = executors.submit(wrapper_get_request,endpoint)
                responses.append(r)
        
        coordinators = []
        for response in responses:
            coordinators.append(response.result().json()["coordinator"])
        
        # If every node starts at the same time and no primary has been elected
        if (coordinators.count(-1) == len(coordinators)):
            self.election()
        else:
            # if we are joining a current running system
            coordinator = coordinators[0]
            
            # if a higher processID joins the system
            # Step1: sync database with the current primary
            # Step2: starts the election
            if (self.node_id > coordinator):
                
                url = self.alive_neighbors[coordinator]

                # call the sync endpoint of current primary
                endpoint = f"http://{url}:{CATALOG_PORT}/sync_database"
                response = requests.get(endpoint, timeout=3.05)
                json_response = response.json()

                # sync up database
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
                    self.announce()
                else:
                    self.election()
            else:
                # if a lower processID joins the system
                # Step1: sync database with the current primary
                # Step2: set the primary of the system as our coordinator

                # sync database
                url = self.alive_neighbors[coordinator]
                endpoint = f"http://{url}:{CATALOG_PORT}/election"
                data = {"node_id": self.node_id}
                response = requests.post(endpoint, json=data, timeout=3.05)
  
    def get_alive_neighbors(self):
        '''
        This checks is performed by a node that is newly joining or in recovering state - 
        to get a list of all the alive nodes in the current systems
        '''
        executors = concurrent.futures.ThreadPoolExecutor(max_workers=len(list(self.neighbors.keys())))
        responses = []
        
        # Checking who is alive
        for id_, url in self.neighbors.items():
            if (id_ != self.node_id):
                endpoint = f"http://{url}:{CATALOG_PORT}/healthcheck"
                r = executors.submit(wrapper_get_request, endpoint)
                responses.append((r, id_))
        
        # Storing the alive neighbors
        for r, id_ in responses:
            if r.result() is not None:
                self.alive_neighbors[int(id_)] = self.neighbors[int(id_)]
    
    def ping_primary(self):
        '''
        For the backup replicas to ping the leader to check if the leader is alive
        If the leader dies, we begin a new election by returning True
        '''

        if (self.coordinator == -1):
            return True

        url = self.neighbors[self.coordinator]
        endpoint = f"http://{url}:{CATALOG_PORT}/info"

        try:
            response = requests.get(endpoint)
        except:  
            response = None
        finally:
            # if our coordinator is alive
            if (response and response.status_code == 200):
                # update our alive neighbors
                response_json = response.json()
                for id_, url in response_json.get("neighbors").items():
                    self.alive_neighbors[int(id_)] = url
                return False
            else:
                self.alive_neighbors.pop(self.coordinator, None)
                return True

    def re_election(self):
        '''
        This function is called if the primary server crashes
        '''
        if len(self.alive_neighbors) == 1:
            self.announce()
        else:
            # send election to those with higher ids
            higher_ids = {id_: url for id_, url in self.alive_neighbors.items() if int(id_) > self.node_id}
            if (len(higher_ids) == 0):
                # if we are the one with the highest id
                self.announce()
            else:
                for id_, url in higher_ids.items():
                    endpoint = f"http://{url}:{CATALOG_PORT}/election"
                    data = {"node_id": self.node_id}
                    response = requests.post(endpoint, json=data, timeout=3.05)


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
    '''
    Function initally called when the node starts - joins the system
    '''

    # get all alive neighbors
    node.get_alive_neighbors()

    if len(node.alive_neighbors) == 0:
        # This means that there is only one node and they are the leader
        # We will have to annouce that the node is a coordinator
        node.announce()
    else:
        # Handle new node entering the system scenario
        node.ready_for_election()

    # Continuously checking if the coordinator is alive
    # if not - ping_response=True - start a re-election
    while(True):
        if (node.coordinator != node.node_id):
            ping_response = node.ping_primary()       
            if not ping_response:
                time.sleep(3)
            else:
                node.coordinator = -1
                node.re_election()
                time.sleep(3)