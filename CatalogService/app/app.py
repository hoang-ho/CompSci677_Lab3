from flask import Flask
from flask_restful import Api
from api.resources import HealthCheck, Query, Buy, PrimaryUpdate, Update, NodeInfo, Election, Coordinator, SyncDatabase, node, prepopulate, logger
from ConsistencyProtocol.PrimaryBackup import BeginElection
import threading
import os
import time
import requests

def start_runner():
    def start_loop():
        not_started = True
        while not_started:
            logger.info('In start loop')
            try:
                r = requests.get('http://127.0.0.1:5002/healthcheck')
                if r.status_code == 200:
                    logger.info('Server started, quiting start_loop')
                    not_started = False
                logger.info("Status code for ping %d" % r.status_code)
            except:
                logger.info('Server not yet started')
            time.sleep(2)

    logger.info('Started runner')
    thread = threading.Thread(target=start_loop)
    thread.start()

class CatalogServiceFlask(Flask):
    def run(self, host=None, port=None, debug=None, load_dotenv=True, **options):
      if not self.debug or os.getenv('WERKZEUG_RUN_MAIN') == 'true':
        with self.app_context():
            prepopulate()
            start_runner()
      super(CatalogServiceFlask, self).run(host=host, port=port,
                                          debug=debug, load_dotenv=load_dotenv, **options)    

app = CatalogServiceFlask(__name__)
api = Api(app)

api.add_resource(HealthCheck, "/healthcheck")
api.add_resource(Query, "/catalog/query")
api.add_resource(Buy, "/catalog/buy")
api.add_resource(Update, "/catalog/update")
api.add_resource(PrimaryUpdate, "/update_database")
api.add_resource(NodeInfo, "/info")
api.add_resource(Election, "/election")
api.add_resource(Coordinator, "/coordinator")
api.add_resource(SyncDatabase, "/sync_database")
# api.add_resource(NodeJoin, "/request_to_sync")


@app.before_first_request
def activate_election():
    thread = threading.Thread(target=BeginElection, args=(node,))
    thread.start()

if __name__ == "__main__":
    # run the application
    app.debug = True
    app.run(host='0.0.0.0', port=5002, debug=True)

'''
Goal:
    - We need a background process/thread that keeps running and check for heartbeat from both backup and primary
    - If we use @app.before_first_request to begin election then it'd be problem if we are syncing via our app 
    because we are posting back to the node that wants to join
    - If we don't use this  @app.before_first_request, then two questions: (1) How to do the background thread
'''
