from bson.regex import Regex
from flask_restful import Resource, reqparse
from pymongo import MongoClient

from app.common.env import *


class Patients(Resource):
    def get(self, vet_id):
        mongo_cli = MongoClient(host=MONGO_HOST)

        patients = list(mongo_cli.db.patients.find(
            {'vet_id': vet_id, 'is_archived': {'$in': [False, None]}},
            projection={'history': False, 'is_archived': False}))

        for patient in patients:
            patient['patient_id'] = patient.pop('_id')

            client = mongo_cli.db.clients.find_one({
                '_id': patient['client_id'],
                'is_archived': {'$in': [False, None]}})
            patient['client_name'] = '{} {}'.format(client['first_name'], client['last_name'])
            patient['client_status'] = client['status']

            orders_count = mongo_cli.db.orders.count({
                'client_id': client['_id'],
                'is_archived': {'$in': [False, None]}})
            patient['client_pending_orders'] = bool(orders_count)

        return {'patients': patients}, 200


class PatientOrders(Resource):
    def get(self, vet_id, patient_id):
        mongo_cli = MongoClient(host=MONGO_HOST)

        orders = list(mongo_cli.db.orders.find(
            {
                'vet_id': vet_id,
                'patient_id': patient_id,
                'is_archived': {'$in': [False, None]}
            },
            projection={'history': False, 'is_archived': False}))

        for order in orders:
            order['order_id'] = order.pop('_id')
            for product in order['order_contents']:
                _ = mongo_cli.db.products.find_one(
                    {'_id': product['product_id']})
                product['image_url'] = _['image_url'] if _ else None
                product['type'] = _['type'] if _ else None
                product['product_name'] = _['product_name'] if _ else None

        return {'orders': orders}, 200


class PatientSearch(Resource):
    def __init__(self):
        super().__init__()

        self._parser_get = reqparse.RequestParser()
        self._parser_get.add_argument('query', required=True)

    def get(self, vet_id):
        args = self._parser_get.parse_args()

        if not args['query']:
            return {'results': []}, 200

        regex = Regex(pattern='^{}.*'.format(args['query']), flags='si')

        mongo_cli = MongoClient(host=MONGO_HOST)
        results = list(mongo_cli.db.patients.find(
            {
                'vet_id': vet_id,
                'name': regex,
                'is_archived': {'$in': [False, None]}
            },
            projection={'history': False, 'is_archived': False}))

        result_ids = {_['_id'] for _ in results}

        clients = mongo_cli.db.clients.aggregate([
            {'$project': {'client_name': {'$concat': ['$first_name', ' ', '$last_name']}, 'email_address': True}},
            {'$match': {'is_archived': {'$in': [False, None]}, 'client_name': regex}}])

        for client in clients:
            pets = list(mongo_cli.db.patients.find({
                'vet_id': vet_id,
                'client_id': client['_id'],
                'is_archived': {'$in': [False, None]}
            }, projection={'is_archived': False, 'history': False}))

            for pet in pets:
                if pet['_id'] not in result_ids:
                    pet['client_name'] = client['client_name']
                    pet['client_email'] = client['email_address']
                    results.append(pet)
                    result_ids.add(pet['_id'])

        for res in results:
            if 'client_name' not in res:
                client = mongo_cli.db.clients.find_one({
                    '_id': res['client_id'],
                    'is_archived': {'$in': [False, None]}})
                res['client_name'] = '{} {}'.format(client['first_name'], client['last_name'])
                res['client_email'] = client['email_address']

            orders_count = mongo_cli.db.orders.count({
                'client_id': client['_id'],
                'is_archived': {'$in': [False, None]}})
            res['client_pending_orders'] = bool(orders_count)

            res['client_status'] = 'Pending'

        return {'results': results}, 200
