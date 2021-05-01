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

    count = 100
    t_cache_sum = 0
    t_nocache_sum = 0
    
    for i in range(count):
        # first lookup is without cache
        logging.info("Iteration: %s ", i)
        t_start = time.time()
        response = requests.get("http://" + frontend + ":5004/lookup/1")
        t_end = time.time()
        t_nocache_sum += (t_end - t_start) * 1000
        
        # second lookup is with cache
        t_start = time.time()
        response = requests.get("http://" + frontend + ":5004/lookup/1")
        t_end = time.time()
        t_cache_sum += (t_end - t_start) * 1000

        # buy to invalidate the cache
        response = requests.put("http://" + frontend + ":5004/buy/1")

        
        # t_total = t_end-t_start
        # t_sum += (t_total*1000)
    logging.info(f'Total response time with cache: {t_nocache_sum}')
    t_nocache_avg = t_nocache_sum/100
    logging.info(f'Average response time with cache: {t_nocache_avg}')

    logging.info(f'Total response time with cache: {t_cache_sum}')
    t_cache_avg = t_cache_sum/100
    logging.info(f'Average response time with cache: {t_cache_avg}')