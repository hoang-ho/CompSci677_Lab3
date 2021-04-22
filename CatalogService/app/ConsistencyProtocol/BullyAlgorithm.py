import os
import requests
import logging
from sys import stdout
import time
import random
from utils import synchronized

CATALOG_HOST = os.getenv("CATALOG_HOST")
CATALOG_PORT = os.getenv("CATALOG_PORT")

logger = logging.getLogger("Catalog-Service")

logger.setLevel(logging.INFO)  # set logger level
logFormatter = logging.Formatter(
    "%(name)-12s %(asctime)s %(levelname)-8s %(filename)s:%(funcName)s %(message)s")
consoleHandler = logging.StreamHandler(stdout)  # set streamhandler to stdout
consoleHandler.setFormatter(logFormatter)
logger.addHandler(consoleHandler)

class Node:
    def __init__(self, node_id, coordinator = -1):
        '''
        node_id: id of the node
        coordinator: id of the coordinator
        election: True if there is an election going on
        '''
        self.node_id = node_id
        self.coordinator = coordinator

def BeginElection(node, wait=True):
    all_ids = get_all_ids()

    # Check if there is no election currently going on
    election_ready = ready_for_election(all_ids)
    logger.info("Election ready? " + str(election_ready))

    if wait:
        timeout = random.randint(5, 10)
        time.sleep(timeout)
        logger.info('timeouting in %s seconds' % timeout)
    
    
    if election_ready:
        logger.info('Starting election in: %s' % node.node_id)
        higher_ids = [id_ for id_ in all_ids if id_ > node.node_id]

        logger.info(' '.join(map(str, higher_ids)))
        
        # we are the node with the highest id
        if (len(higher_ids) == 0):
            node.coordinator = node.node_id
            logger.info("Announcing Coordinator as %d " % node.node_id)
            announce(node.node_id)
        else: 
            # Send election message to node with higher id
            if election(node.node_id, higher_ids) == False:
                # If none of the node with higher id is alive
                # This node becomes the leader
                node.coordinator = node.node_id
                announce(node.node_id)

def get_all_ids():
    return [int(val) for val in os.getenv("LIST_IDS").split(",")]

def ready_for_election(all_ids):
    coordinator_details = []

    for id_ in all_ids:
        url = f"http://{CATALOG_HOST}_{id_}:{CATALOG_PORT}/info"
        logger.info("Sending request to " + url)
        r = requests.get(url)
        data = r.json()
        coordinator_details.append(data["coordinator"])
    
    # if there is some leader getting chosen, wait for announcement
    if (coordinator_details.count(-1) == len(coordinator_details)):
        return True
    else:
        return False


def election(node_id, higher_ids):
    data = {"node_id": node_id}
    response_codes = []

    for id_ in higher_ids:
        url = f"http://{CATALOG_HOST}_{id_}:{CATALOG_PORT}/election"

        response = requests.post(url, json=data)
        response_codes.append(response.status_code)

    if 200 in response_codes:
        return True
    else:
        return False

def announce(coordinator):
    all_ids = get_all_ids()

    data = {"coordinator": coordinator}

    for id_ in all_ids:
        if id_ != coordinator:
            url = f"http://{CATALOG_HOST}_{id_}:{CATALOG_PORT}/coordinator"
            response = requests.post(url, json=data)

            if (response.status_code == 200):
                logger.info("Done notifying node %d" % id_)
            else:
                logger.info("Could not notify node %d"  % id_)
