from flask import Flask
from flask_restful import Api
from api.resources import Query, Buy, Update, prepopulate
import os


class CatalogServiceFlask(Flask):
  def run(self, host=None, port=None, debug=None, load_dotenv=True, **options):
    if not self.debug or os.getenv('WERKZEUG_RUN_MAIN') == 'true':
      with self.app_context():
        prepopulate()
    super(CatalogServiceFlask, self).run(host=host, port=port,
                                         debug=debug, load_dotenv=load_dotenv, **options)


app = CatalogServiceFlask(__name__)
api = Api(app)
api.add_resource(Query, "/catalog/query")
api.add_resource(Buy, "/catalog/buy")
api.add_resource(Update, "/catalog/update")


if __name__ == "__main__":
    # run the application
    app.debug = True
    app.run(host='0.0.0.0', port=5002)
