from flask_restful import Resource
from pymongo import MongoClient

from app.common.env import *


class CareTeam(Resource):
    def get(self, client_id):
        mongo_cli = MongoClient(host=MONGO_HOST)

        orders = list(mongo_cli.db.orders.find(
            {'client_id': client_id, 'is_archived': {'$in': [False, None]}}))
        subscriptions = list(mongo_cli.db.subscriptions.find(
            {'client_id': client_id, 'is_archived': {'$in': [False, None]}}))
        vet_ids = {_['vet_id'] for _ in orders} | {_['vet_id']
                                                   for _ in subscriptions}
        vet_projection = {
            'first_name': True,
            'last_name': True,
            'email_address': True,
            'image_url': True,
            'phone': True,
            'address': True
        }
        vets = []
        for vet_id in vet_ids:
            vet = mongo_cli.db.vets.find_one({'_id': vet_id, 'is_archived': {
                '$in': [False, None]}}, projection=vet_projection)
            vet['vet_id'] = vet.pop('_id')
            vet['phone'] = vet.pop('phone')['work']
            vet['name'] = '{} {}'.format(
                vet.pop('first_name'), vet.pop('last_name'))
            vets.append(vet)

        pharmacy_ids = {_.get('pharmacy_id') for _ in orders} | {
            _.get('pharmacy_id') for _ in subscriptions}

        if None in pharmacy_ids:
            pharmacy_ids.remove(None)

        pharmacy_projection = {
            'name': True,
            'email': True,
            'phone': True,
            'image_url': True,
            'address': True
        }
        pharmacies = []
        for pharmacy_id in pharmacy_ids:
            pharm = mongo_cli.db.pharmacies.find_one({'_id': pharmacy_id,
                                                      'is_archived': {'$in': [False, None]}},
                                                     projection=pharmacy_projection)
            pharm['pharmacy_id'] = pharm.pop('_id')
            pharm['email_address'] = pharm.pop('email')
            pharmacies.append(pharm)

        return {'vets': vets, 'pharmacies': pharmacies}, 200
