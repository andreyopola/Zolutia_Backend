import datetime

from flask_restful import Resource, reqparse
from pymongo import MongoClient

from app.common import parser
from app.common.env import *
from app.common.fake_request import FakeRequest


class Orders(Resource):
    def __init__(self):
        super().__init__()

        self._parser_get = reqparse.RequestParser()
        self._parser_get.add_argument('type', choices=('rx', 'otc',))
        self._parser_get.add_argument(
            'status', dest='order_status', choices=('open', 'closed',))
        self._parser_get.add_argument('offset', type=int, default=0)
        self._parser_get.add_argument('limit', type=int, default=20)

    def get(self, vet_id):
        args = {k: v for k, v in self._parser_get.parse_args().items() if v is not None}
        args['vet_id'] = vet_id
        args['is_archived'] = {'$in': [False, None]}

        skip = args.pop('offset')
        limit = args.pop('limit')

        order_type = None
        if args.get('type'):
            order_type = args.pop('type')

        if 'order_status' in args:
            if args['order_status'] == 'open':
                args['order_status'] = {'$in': ['pending', 'processing']}
            elif args['order_status'] == 'closed':
                args['order_status'] = {'$in': ['shipped', 'delivered', 'fulfilled']}

        mongo_cli = MongoClient(host=MONGO_HOST)
        orders = list(mongo_cli.db.orders.find(args, limit=limit, skip=skip))
        orders_count = mongo_cli.db.orders.count({'vet_id': vet_id, 'is_archived': {'$in': [False, None]}})

        if order_type:
            for order in orders[:]:
                rx_flag = False
                for product_ref in order['order_contents']:
                    product = mongo_cli.db.products.find_one(
                        {'_id': product_ref['product_id'], 'is_archived': {'$in': [False, None]}})
                    if product and product['type'].lower() == 'rx':
                        rx_flag = True
                        if order_type.lower() == 'rx':
                            break
                if rx_flag and order_type.lower() != 'rx':
                    orders.remove(order)
                elif not rx_flag and order_type.lower() == 'rx':
                    orders.remove(order)

        for order in orders:
            order['order_id'] = order.pop('_id')

            client = mongo_cli.db.clients.find_one(
                {
                    '_id': order['client_id'],
                    'is_archived': {'$in': [None, False]}
                },
                projection={'first_name': True, 'last_name': True}) or {}
            order['client_name'] = '{} {}'.format(client.get('first_name'), client.get('last_name'))

            patient = mongo_cli.db.patients.find_one(
                {
                    '_id': order['patient_id'],
                    'is_archived': {'$in': [None, False]}
                },
                projection={'name': True}) or {}
            order['patient_name'] = patient.get('name')

            for product in order['order_contents']:
                _ = mongo_cli.db.products.find_one(
                    {'_id': product['product_id']})
                product['image_url'] = _['image_url'] if _ else None
                product['type'] = _['type'] if _ else None
                product['product_name'] = _['product_name'] if _ else None

        return {'orders': orders, 'count': orders_count}, 200


class Order(Resource):
    def __init__(self):
        super().__init__()

        self._parser_put = reqparse.RequestParser()
        self._parser_put.add_argument('order_contents', type=FakeRequest,
                                      action='append', required=True)

        self._parser_order = parser.order.copy()

    def put(self, vet_id, order_id):
        mongo_cli = MongoClient(host=MONGO_HOST)
        order = mongo_cli.db.orders.find_one(
            {'_id': order_id, 'order_status': {'$in': ['pending', 'processing']}})
        if not order:
            return {'updated': False}, 200

        args = self._parser_put.parse_args()

        subtotal = 0.0

        prods = []
        for product in args['order_contents']:
            product = self._parser_order.parse_args(req=product)
            prods.append(product)
            subtotal += float(product['product_price'])  # * int(product['quantity'])
        args['order_contents'] = prods

        args['subtotal_price'] = str(round(subtotal, 2))

        total = subtotal + float(order['shipping_amount']) + float(order['tax'])
        args['total_price'] = str(round(total, 2))

        args['history.modified_on'] = datetime.datetime.utcnow()

        result = mongo_cli.db.orders.update_one(
            {'_id': order_id, 'vet_id': vet_id}, {'$set': args})

        return {'updated': bool(result.modified_count)}, 200


class Feedbacks(Resource):
    def get(self, vet_id):
        mongo_cli = MongoClient(host=MONGO_HOST)

        projection = {
            'client_id': True,
            'patient_id': True,
            'feedback.is_satisfied': True,
            'feedback.comments': True,
            'delivered_date': True
        }

        orders = list(mongo_cli.db.orders.find(
            {
                'vet_id': vet_id,
                'feedback.is_feedback_read': False,
                'is_archived': {'$in': [None, False]}
            },
            projection=projection))

        for order in orders:
            order['order_id'] = order.pop('_id')
            client = mongo_cli.db.clients.find_one(
                {
                    '_id': order['client_id'],
                    'is_archived': {'$in': [None, False]}
                },
                projection={'first_name': True, 'last_name': True})
            if client:
                order['client_name'] = '{} {}'.format(client['first_name'], client['last_name'])

            patient = mongo_cli.db.patients.find_one(
                {
                    '_id': order['patient_id'],
                    'is_archived': {'$in': [None, False]}
                },
                projection={'name': True})
            if patient:
                order['patient_name'] = patient['name']

        return {'orders': orders}, 200


class Feedback(Resource):
    def put(self, vet_id, order_id):
        mongo_cli = MongoClient(host=MONGO_HOST)

        payload = {
            'feedback.is_feedback_read': True,
            'history.modified_on': datetime.datetime.utcnow()
        }

        result = mongo_cli.db.orders.update_one(
            {'_id': order_id, 'vet_id': vet_id}, {'$set': payload})

        return {'updated': bool(result.modified_count)}, 200
