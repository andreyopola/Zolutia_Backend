from bson.objectid import ObjectId
from bson.regex import Regex
from flask_restful import Resource, abort, reqparse
from pymongo import MongoClient

from app.common.env import *


class Search(Resource):
    def __init__(self):
        super().__init__()

        self._parser = reqparse.RequestParser()
        self._parser.add_argument('type', required=True)
        self._parser.add_argument('q', required=True)

    def get(self, vet_id):
        args = self._parser.parse_args()

        mongo_cli = MongoClient(host=MONGO_HOST)
        regex = Regex(pattern='^{}.*'.format(args['q']), flags='si')

        res = {'results': []}

        if args['type'] == 'clients':
            pet_owners = {pet['client_id'] for pet in
                          mongo_cli.db.patients.find(
                              {'vet_id': ObjectId(vet_id), 'is_archived': {'$in': [False, None]}},
                              projection={'client_id': True})}
            clients = mongo_cli.db.clients.aggregate([
                {'$project': {'client_name': {'$concat': ['$first_name', ' ', '$last_name']}, 'email_address': True}},
                {'$match': {'is_archived': {'$in': [False, None]}, 'client_name': regex}}])

            for c in clients:
                if c['_id'] in pet_owners:
                    client = {
                        'client_name': c['client_name'],
                        'client_email': c['email_address'],
                        'client_id': str(c['_id'])
                    }
                    res['results'].append(client)

        elif args['type'] == 'products':
            vet = mongo_cli.db.vets.find_one(
                {'_id': ObjectId(vet_id), 'is_archived': {'$in': [False, None]}})
            if vet is None:
                return res, 200
            else:
                hospital_id = vet['hospital_id']

            # formulary = {form['product_id'] for form in
            #              mongo_cli.db.hospitals.find_one({'_id': hospital_id, 'is_archived': {'$in': [False, None]}},
            #                                              projection={'formulary.product_id': True})['formulary']}

            products = mongo_cli.db.products.find(
                {'product_name': regex, 'is_archived': {'$in': [False, None]}})

            for p in products:
                product = {
                    'product_name': p['product_name'],
                    'product_id': str(p['_id'])
                }
                res['results'].append(product)

        else:
            abort(400, message='Unknown type')

        return res
