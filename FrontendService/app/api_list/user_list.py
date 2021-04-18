from flask_restful import Resource

class UserList(Resource):

    # A list of available API endpoints at the Front-end Server

    api_list = {
        'search': 'GET <address>:<port>/search/<topic_name>',
        'lookup': 'GET <address>:<port>/lookup/<item_id>',
        'buy': 'POST <address>:<port>/buy/<item_id>'
    }

    def get(self):
        return {
            'List': 'Available APIs',
            **self.api_list
        }