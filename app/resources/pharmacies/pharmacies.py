import datetime

from flask_restful import Resource, abort, reqparse
from pymongo import MongoClient

from app.common import parser
from app.common.env import *
from app.common.fake_request import FakeRequest
from app.common.types import strphone


class Pharmacy(Resource):
    def __init__(self):
        super().__init__()

        self._parser_put = reqparse.RequestParser()
        self._parser_put.add_argument('name')
        self._parser_put.add_argument('phone', type=strphone)
        self._parser_put.add_argument('fax')
        self._parser_put.add_argument('image_url')
        self._parser_put.add_argument('address', type=FakeRequest)

        self._parser_address = parser.address.copy()

    def get(self, pharmacy_id):
        mongo_cli = MongoClient(host=MONGO_HOST)

        projection = {
            'is_archived': False,
            'history': False,
            '_id': False
        }

        pharmacy = mongo_cli.db.pharmacies.find_one({'_id': pharmacy_id, 'is_archived': {'$in': [None, False]}},
                                                    projection=projection)

        if not pharmacy:
            abort(404, message='Not found')

        return pharmacy, 200

    def put(self, pharmacy_id):
        args = {k: v for k, v in self._parser_put.parse_args().items() if v is not None}

        if args.get('address') is not None:
            for k, v in self._parser_address.parse_args(req=args['address']).items():
                if v is not None:
                    args['address.{}'.format(k)] = v
            args.pop('address')

        args['history.modified_on'] = datetime.datetime.utcnow()

        mongo_cli = MongoClient(host=MONGO_HOST)
        result = mongo_cli.db.pharmacies.update_one({'_id': pharmacy_id}, {'$set': args})

        return {'updated': bool(result.modified_count)}, 200
