import datetime

from flask_restful import Resource, reqparse
from pymongo import MongoClient

from app.common.env import *


class Vets(Resource):
    def get(self, hospital_id):
        mongo_cli = MongoClient(host=MONGO_HOST)

        projection = {
            'first_name': True,
            'last_name': True,
            'is_hospital_admin': True,
            "email_address": True,
            "phone": True
        }

        vets = [v for v in mongo_cli.db.vets.find(
            {
                'hospital_id': hospital_id,
                'is_archived': {'$in': [False, None]}
            },
            projection=projection)]

        for vet in vets:
            vet['vet_id'] = vet.pop('_id')
            vet['name'] = "{} {}".format(vet.pop('first_name'), vet.pop('last_name'))

        return {'vets': vets}, 200


class Vet(Resource):
    def __init__(self):
        super().__init__()

        self._parser_put = reqparse.RequestParser()
        self._parser_put.add_argument('is_hospital_admin', type=bool, required=True)

    def put(self, hospital_id, vet_id):
        mongo_cli = MongoClient(host=MONGO_HOST)

        args = self._parser_put.parse_args()
        args['history.modified_on'] = datetime.datetime.utcnow()

        result = mongo_cli.db.vets.update_one(
            {'_id': vet_id, 'hospital_id': hospital_id},
            {'$set': args}
        )

        return {'updated': bool(result.modified_count)}, 200
