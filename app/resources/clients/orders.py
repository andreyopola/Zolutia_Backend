import datetime

from flask_restful import Resource, abort, reqparse
from pymongo import MongoClient

from app.common.env import *


class Orders(Resource):
    def __init__(self):
        super().__init__()

        self._parser_get = reqparse.RequestParser()
        self._parser_get.add_argument('type')

    def get(self, client_id):
        args = {k: v for k, v in self._parser_get.parse_args().items() if v is not None}
        args['client_id'] = client_id
        args['is_archived'] = {'$in': [False, None]}

        if args.get('type'):
            args['order_type'] = args.pop('type')

        projection = {
            'history': False,
            'is_archived': False
        }

        mongo_cli = MongoClient(host=MONGO_HOST)
        orders = list(mongo_cli.db.orders.find(args, projection=projection))

        for order in orders:
            order['order_id'] = order.pop('_id')

            patient = mongo_cli.db.patients.find_one(
                {'_id': order['patient_id']},
                {'name': True})
            if patient:
                order['patient_name'] = patient['name']

            for product in order['order_contents']:
                _ = mongo_cli.db.products.find_one(
                    {'_id': product['product_id']})
                product['product_name'] = _['product_name'] if _ else None
                product['image_url'] = _['image_url'] if _ else None

        return {'orders': orders}, 200


class Order(Resource):
    def __init__(self):
        super().__init__()

        self._parser_put = reqparse.RequestParser()
        self._parser_put.add_argument('comments')
        self._parser_put.add_argument('is_satisfied', required=True, type=bool)

    def get(self, client_id, order_id):
        mongo_cli = MongoClient(host=MONGO_HOST)

        projection = {
            'history': False,
            'is_archived': False,
            '_id': False
        }

        order = mongo_cli.db.orders.find_one(
            {'_id': order_id, 'client_id': client_id,
             'is_archived': {'$in': [False, None]}},
            projection=projection
        )
        if not order:
            abort(404, message='Not found')

        patient = mongo_cli.db.patients.find_one(
            {'_id': order['patient_id']},
            {'name': True})
        if patient:
            order['patient_name'] = patient['name']

        for product in order['order_contents']:
            _ = mongo_cli.db.products.find_one({'_id': product['product_id']})
            product['product_name'] = _['product_name'] if _ else None
            product['image_url'] = _['image_url'] if _ else None

        return order, 200

    def put(self, client_id, order_id):
        args = self._parser_put.parse_args()
        args['timestamp'] = datetime.datetime.utcnow()
        args['is_feedback_read'] = False

        mongo_cli = MongoClient(host=MONGO_HOST)
        result = mongo_cli.db.orders.update_one(
            {'_id': order_id, 'client_id': client_id}, {'$set': {'feedback': args}})

        return {'updated': bool(result.modified_count)}, 200
