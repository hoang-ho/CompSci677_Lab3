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

    count = 1000
    t_sum = 0
    t_avg = 0
    
    for i in range(count):
        t_start = time.time()
        response = requests.get("http://" + frontend + ":5004/search/distributed-systems")
        t_end = time.time()
        logging.info("Search query: %s ", i)
        t_total = t_end-t_start
        t_sum += (t_total*1000)

    logging.info(f'Total time: {t_sum}')
    t_avg = t_sum/1000
    logging.info(f'Average time: {t_avg}')
