import datetime

from flask_restful import Resource
from pymongo import MongoClient

from app.common.env import *


class Patient(Resource):
    def delete(self, client_id, patient_id):
        mongo_cli = MongoClient(host=MONGO_HOST)
        result = mongo_cli.db.patients.update_one(
            {'_id': patient_id, 'client_id': client_id},
            {
                '$set': {
                    'is_archived': True,
                    'history.archived_on': datetime.datetime.utcnow()
                }
            }
        )

        return {'deleted': bool(result.modified_count)}, 200


class Patients(Resource):
    def get(self, client_id):
        mongo_cli = MongoClient(host=MONGO_HOST)

        projection = {
            'history': False,
            'is_archived': False
        }

        pets = list(mongo_cli.db.patients.find(
            {'client_id': client_id, 'is_archived': {'$in': [False, None]}},
            projection=projection)
        )

        for pet in pets:
            pet['patient_id'] = pet.pop('_id')

        return {'patients': pets}
