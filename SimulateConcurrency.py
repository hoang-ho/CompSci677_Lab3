import argparse
import requests
import logging
import threading
import time
import random
logging.getLogger().setLevel(logging.INFO)


def main(frontend, catalog):
    frontend_buy = "http://" + frontend + ":5004/buy/2"
    catalog_update = "http://" + catalog + ":5002/catalog/update"

    api = [frontend_buy, catalog_update]

    data = {"id": 2, "stock": 2000, "cost": 2000}

    call = random.choice(api)
    logging.info("Calling request %s at timestamp %s", call, time.time())
    if (call == api[1]):
        logging.info("Calling request %s at timestamp %s", call, time.time())
        response = requests.put(call, json=data)
    else:
        response = requests.post(call)

    logging.info("Response: %s at time stamp %s", response.text, time.time())


if __name__ == "__main__":
    

    parser = argparse.ArgumentParser()
    parser.add_argument("--front-end-dns", required=True)
    parser.add_argument("--catalog-dns", required=True)
    args = parser.parse_args()
    
    frontend = args.front_end_dns
    catalog = args.catalog_dns

    response = requests.get("http://" + frontend + ":5004/lookup/2")

    logging.info(
        "Look up the book stock and cost before update and buy: %s ", response.text)

    threads = list()
    for index in range(3):
        logging.info("Main    : create and start thread %d.", index)
        x = threading.Thread(target=main, args=(frontend, catalog))
        threads.append(x)
        x.start()

    for index, thread in enumerate(threads):
        logging.info("Main    : before joining thread %d.", index)
        thread.join()
        logging.info("Main    : thread %d done", index)

    response = requests.get("http://" + frontend + ":5004/lookup/2")

    logging.info(
        "Look up the book stock and cost after update and buy: %s ", response.text)
