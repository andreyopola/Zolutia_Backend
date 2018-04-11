from flask_restful import Resource
from pymongo import MongoClient

from app.common.env import *


class Clients(Resource):
    def get(self, vet_id, client_id):
        mongo_cli = MongoClient(host=MONGO_HOST)

        if mongo_cli.db.patients.count({'vet_id': vet_id, 'client_id': client_id}) == 0:
            return {}, 200

        projection = {
            '_id': False,
            'billing_address': False,
            'shipping_address': False,
            'history': False,
            'is_archived': False,
            'card': False
        }

        patient_projection = {
            "name": True
        }

        client = mongo_cli.db.clients.find_one(
            {'_id': client_id, 'is_archived': {'$in': [False, None]}},
            projection=projection)

        patients = mongo_cli.db.patients.find(
            {'client_id': client_id, 'is_archived': {'$in': [False, None]}},
            projection=patient_projection)

        client['patients'] = []
        for patient in patients:
            patient['patient_id'] = patient.pop('_id')
            patient['patient_name'] = patient.pop('name')
            client['patients'].append(patient)

        return client, 200
