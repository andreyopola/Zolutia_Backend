import datetime

from bson.objectid import ObjectId
from flask_restful import Resource, reqparse
from pymongo import MongoClient

from app.common import parser
from app.common.env import *
from app.common.fake_request import FakeRequest


class Vets(Resource):
    def __init__(self):
        super().__init__()

        self._parser_post = reqparse.RequestParser()
        object_id_post_fields = ['user_id', 'hospital_id']
        for field in object_id_post_fields:
            self._parser_post.add_argument(field, required=True, type=ObjectId)
        str_post_fields = ['first_name', 'last_name', 'email_address']
        for field in str_post_fields:
            self._parser_post.add_argument(field, required=True)
        self._parser_post.add_argument('phone', type=FakeRequest, required=True)

        self._parser_address = parser.address.copy()
        self._parser_phone = parser.phone.copy()

        self._parser_put = reqparse.RequestParser()
        object_id_put_fields = ['user_id', 'hospital_id']
        for field in object_id_put_fields:
            self._parser_put.add_argument(field, type=ObjectId)
        str_put_fields = ['first_name', 'last_name', 'dea', 'npi', 'state_license', 'image_url', 'specialty', 'title']
        for field in str_put_fields:
            self._parser_put.add_argument(field)
        fr_put_fields = ['phone', 'address']
        for field in fr_put_fields:
            self._parser_put.add_argument(field, type=FakeRequest)

    def get(self, vet_id):
        mongo_cli = MongoClient(host=MONGO_HOST)

        projection_fields = ['_id', 'fax', 'treatment_plan_templates', 'history', 'is_archived']
        vet_projection = {field: False for field in projection_fields}

        vet = mongo_cli.db.vets.find_one(
            {'_id': ObjectId(vet_id), 'is_archived': {'$in': [False, None]}},
            projection=vet_projection)

        return vet, 200

    def post(self):
        args = self._parser_post.parse_args()
        args['phone'] = self._parser_phone.parse_args(req=args['phone'])
        args['address'] = self._parser_address.parse_args(req=args['address'])
        args['history'] = {'created_on': datetime.datetime.utcnow()}

        mongo_cli = MongoClient(host=MONGO_HOST)
        vet_id = mongo_cli.db.vets.insert_one(args).inserted_id

        return {'vet_id': vet_id}, 200

    def put(self, vet_id):
        args = {k: v for k, v in self._parser_put.parse_args().items() if v is not None}
        if len(args) == 0:
            return {'updated': False}, 200

        if 'phone' in args:
            args['phone'] = {k: v for k, v in
                             self._parser_phone.parse_args(req=args['phone']).items() if v is not None}
        if 'address' in args:
            args['address'] = {k: v for k, v in
                               self._parser_address.parse_args(req=args['address']).items() if v is not None}
        args['history.modified_on'] = datetime.datetime.utcnow()

        mongo_cli = MongoClient(host=MONGO_HOST)
        resp = mongo_cli.db.vets.update_one({'_id': ObjectId(vet_id)}, {'$set': args})

        return {'updated': bool(resp.modified_count)}, 200
