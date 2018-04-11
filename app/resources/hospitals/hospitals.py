import datetime

from flask_restful import Resource, reqparse
from pymongo import MongoClient

from app.common import parser
from app.common.env import *
from app.common.fake_request import FakeRequest
from app.common.types import strphone


class Hospital(Resource):
    def __init__(self):
        super().__init__()

        self._parser_put = reqparse.RequestParser()
        self._parser_put.add_argument('name')
        self._parser_put.add_argument('phone', type=strphone)
        self._parser_put.add_argument('fax')
        self._parser_put.add_argument('email')
        self._parser_put.add_argument('address', type=FakeRequest)

        self._parser_address = parser.address.copy()

    def get(self, hospital_id):
        mongo_cli = MongoClient(host=MONGO_HOST)

        projection = {
            '_id': False,
            'name': True,
            'email': True,
            'phone': True,
            'address': True
        }

        hospital = mongo_cli.db.hospitals.find_one(
            {'_id': hospital_id, 'is_archived': {'$in': [False, None]}}, projection=projection)
        if hospital is None:
            return {}, 200
        else:
            return hospital, 200

    def put(self, hospital_id):
        mongo_cli = MongoClient(host=MONGO_HOST)

        args = {k: v for k, v in self._parser_put.parse_args().items() if v is not None}
        if 'address' in args:
            args['address'] = self._parser_address.parse_args(req=args['address'])
        args['history.modified_on'] = datetime.datetime.utcnow()

        result = mongo_cli.db.hospitals.update_one({'_id': hospital_id}, {'$set': args})

        return {'updated': bool(result.modified_count)}, 200
