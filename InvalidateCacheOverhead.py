import argparse
import requests
import logging
import threading
import time
import random
logging.getLogger().setLevel(logging.INFO)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--front-end-dns", required=True)
    args = parser.parse_args()

    frontend = args.front_end_dns

    response = requests.get("http://" + frontend + ":5004/lookup/1")
    t_start = time.time()
    response = requests.get("http://" + frontend + ":5004/lookup/1")
    t_end = time.time()
    t_diff = (t_end - t_start) * 1000
    logging.info(f"Response time for cache lookup {t_diff}")

    response = requests.post("http://" + frontend + ":5004/buy/1")

    t_start = time.time()
    response = requests.get("http://" + frontend + ":5004/lookup/1")
    t_end = time.time()
    t_diff = (t_end - t_start) * 1000
    logging.info(f"Response time for cache miss lookup {t_diff}")