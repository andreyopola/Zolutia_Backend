import datetime

from flask_restful import Resource, reqparse
from pymongo import MongoClient

from app.common.env import *
from app.common.fake_request import FakeRequest


class Payments(Resource):
    def __init__(self):
        self._parser_post = reqparse.RequestParser()
        self._parser_post.add_argument('card', type=FakeRequest, required=True)

        self._parser_card = reqparse.RequestParser()
        self._parser_card.add_argument('card_number', required=True)
        self._parser_card.add_argument('expiry_date', required=True)
        self._parser_card.add_argument('cardholder_name', required=True)

    def get(self, client_id):
        mongo_cli = MongoClient(host=MONGO_HOST)

        order = mongo_cli.db.orders.find_one(
            {'client_id': client_id, 'is_archived': {'$in': [False, None]}},
            sort=[('history.created_on', -1)])

        if order:
            try:
                if order['card'] and order['card']['last_4']:
                    return order['card']['last_4'], 200
            except KeyError:
                pass

        return {}, 204

    def post(self, client_id):
        args = self._parser_post.parse_args()
        card = self._parser_card.parse_args(req=args['card'])

        mongo_cli = MongoClient(host=MONGO_HOST)
        result = mongo_cli.db.clients.update_one(
            {'_id': client_id},
            {'$set': {
                'card': card,
                'history.modified_on': datetime.datetime.utcnow()
            }})

        return {'updated': bool(result.modified_count)}, 200
