import datetime

from flask_restful import Resource, abort, reqparse
from pymongo import MongoClient

from app.common import notification
from app.common.env import *


class Order(Resource):
    def __init__(self):
        super().__init__()

        self._parser_put = reqparse.RequestParser()
        self._parser_put.add_argument('status', dest='order_status')
        self._parser_put.add_argument('tracking_number')

    def get(self, pharmacy_id, order_id):
        args = {'pharmacy_id': pharmacy_id, '_id': order_id, 'is_archived': {'$in': [False, None]}}

        projection = {
            'is_archived': False,
            'history': False,
            'card': False,
            '_id': False
        }

        mongo_cli = MongoClient(host=MONGO_HOST)
        order = mongo_cli.db.orders.find_one(args, projection=projection)

        if not order:
            abort(404, message='Not found')

        client = mongo_cli.db.clients.find_one({'_id': order['client_id']})
        order['client_name'] = '{} {}'.format(client['first_name'], client['last_name'])
        order['client_email'] = client['email_address']
        order['client_phone'] = client['phone']

        patient = mongo_cli.db.patients.find_one({'_id': order['patient_id']})
        order['patient_name'] = patient['name']

        vet = mongo_cli.db.vets.find_one({'_id': order['vet_id']})
        order['vet_name'] = '{} {}'.format(vet['first_name'], vet['last_name'])

        hospital = mongo_cli.db.hospitals.find_one({'_id': order['hospital_id']})
        order['hospital_name'] = hospital['name']

        for product in order['order_contents']:
            p = mongo_cli.db.products.find_one({'_id': product['product_id']})
            product['product_name'] = p['product_name']
            product['image_url'] = p['image_url']
            product['type'] = p['type']

        return order, 200

    def put(self, pharmacy_id, order_id):
        args = {k: v for k, v in self._parser_put.parse_args().items() if v is not None}
        if not args:
            return {'updated': False}, 200

        args['history.modified_on'] = datetime.datetime.utcnow()
        args['order_status'] = args['order_status'].lower()

        mongo_cli = MongoClient(host=MONGO_HOST)
        result = mongo_cli.db.orders.update_one(
            {'_id': order_id, 'pharmacy_id': pharmacy_id}, {'$set': args})

        order = mongo_cli.db.orders.find_one({'_id': order_id},
                                             {'order_number': 1, 'client_id': 1, 'tracking_number': 1})
        order_no = order.get('order_number', None)
        client_id = order.get('client_id', None)
        tracking_number = order.get('tracking_number', None)
        if client_id and order_no and tracking_number:
            notification.notify_client_shipping(client_id, order_no, tracking_number)

        return {'updated': bool(result.modified_count)}, 200


class Orders(Resource):
    def get(self, pharmacy_id):
        args = {'pharmacy_id': pharmacy_id, 'is_archived': {'$in': [False, None]}}

        projection = {
            'ordered_date': True,
            'order_status': True,
            'vet_id': True,
            'hospital_id': True,
            'client_id': True,
            'patient_id': True,
            'order_number': True
        }

        mongo_cli = MongoClient(host=MONGO_HOST)
        orders = list(mongo_cli.db.orders.find(args, projection=projection))

        for order in orders:
            order['order_id'] = order.pop('_id')

            client = mongo_cli.db.clients.find_one({'_id': order['client_id']})
            order['client_name'] = '{} {}'.format(client['first_name'], client['last_name'])
            order['client_email'] = client['email_address'] if client else ""
            order.pop('client_id')

            patient = mongo_cli.db.patients.find_one({'_id': order['patient_id']})
            order['patient_name'] = patient['name'] if patient else ""
            order.pop('patient_id')

            vet = mongo_cli.db.vets.find_one({'_id': order['vet_id']})
            order['vet_name'] = '{} {}'.format(vet['first_name'], vet['last_name']) if vet else ""
            order.pop('vet_id')

            hospital = mongo_cli.db.hospitals.find_one({'_id': order['hospital_id']})
            order['hospital_name'] = hospital['name'] if hospital else ""
            order.pop('hospital_id')

        return {'orders': orders}, 200
