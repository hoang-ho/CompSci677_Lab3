import argparse
import requests
import logging
import threading
import time
import random
logging.getLogger().setLevel(logging.INFO)


def main(frontend):
    response = requests.get("http://" + frontend + ":5004/search/distributed-systems")


if __name__ == "__main__":
    

    parser = argparse.ArgumentParser()
    parser.add_argument("--front-end-dns", required=True)
    args = parser.parse_args()
    
    frontend = args.front_end_dns

    i = 0
    t_sum = 0
    t_avg = 0

    while(i < 1000):
        logging.info(f'iteration: {i}')
        t_start = list()
        threads = list()
        for index in range(5):

            x = threading.Thread(target=main, args=(frontend,))
            threads.append(x)
            t_start.append(time.time())
            x.start()

        for index, thread in enumerate(threads):
            thread.join()
            diff = time.time() - t_start[index]
            t_sum += diff*1000

        i += 5
    
    logging.info(f'Total time: {t_sum}')
    t_avg = t_sum/1000
    logging.info(f'Average time: {t_avg}')


