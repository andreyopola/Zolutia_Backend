import datetime

from bson.objectid import ObjectId
from flask_restful import Resource, reqparse
from pymongo import MongoClient

from app.common import notification
from app.common import parser
from app.common import registration
from app.common.datetime import strptime
from app.common.env import *
from app.common.fake_request import FakeRequest


class Vet(Resource):
    def __init__(self):
        super().__init__()

        self._parser_put = reqparse.RequestParser()
        self._parser_put.add_argument('hospital_id', type=ObjectId)
        self._parser_put.add_argument('suffix')
        self._parser_put.add_argument('first_name')
        self._parser_put.add_argument('last_name')
        self._parser_put.add_argument('email_address')
        self._parser_put.add_argument('specialty')
        self._parser_put.add_argument('date_of_birth', type=strptime)
        self._parser_put.add_argument('dea')
        self._parser_put.add_argument('npi')
        self._parser_put.add_argument('gender')
        self._parser_put.add_argument('state_license')
        self._parser_put.add_argument('is_hospital_admin', type=bool)
        self._parser_put.add_argument('phone', type=FakeRequest)
        self._parser_put.add_argument('address', type=FakeRequest)

        self._parser_address = parser.address.copy()
        self._parser_phone = parser.phone.copy()

    def get(self, vet_id):
        projection = {
            'suffix': True,
            'first_name': True,
            'last_name': True,
            'specialty': True,
            'image_url': True,
            'email_address': True,
            'phone': True,
            'address': True,
            'state_license': True,
            'is_hospital_admin': True,
            'hospital_id': True,
            'gender': True,
            'date_of_birth': True,
            'status': True,
            '_id': False
        }

        mongo_cli = MongoClient(host=MONGO_HOST)

        vet = mongo_cli.db.vets.find_one(
            {
                '_id': vet_id,
                'is_archived': {'$in': [None, False]}
            },
            projection=projection)

        if not vet:
            return {}, 204

        hospital = mongo_cli.db.hospitals.find_one(
            {
                '_id': vet['hospital_id'], 'is_archived': {'$in': [None, False]}
            },
            projection={'name': True, '_id': False})
        vet['hospital_name'] = hospital['name']

        return vet, 200

    def put(self, vet_id):
        args = {k: v for k, v in self._parser_put.parse_args().items() if v is not None}
        if 'phone' in args:
            args['phone'] = {k: v for k, v in
                             self._parser_phone.parse_args(req=args['phone']).items() if v is not None}
        if 'address' in args:
            args['address'] = {k: v for k, v in
                               self._parser_address.parse_args(req=args['address']).items() if v is not None}
        args['history.modified_on'] = datetime.datetime.utcnow()

        mongo_cli = MongoClient(host=MONGO_HOST)

        result = mongo_cli.db.vets.update_one({'_id': vet_id}, {'$set': args})

        return {'updated': bool(result.modified_count)}, 200

    def delete(self, vet_id):
        mongo_cli = MongoClient(host=MONGO_HOST)

        result = mongo_cli.db.vets.update_one({'_id': vet_id},
                                              {'$set': {
                                                  'is_archived': True,
                                                  'history.archived_on': datetime.datetime.utcnow()}})

        if result.modified_count:
            vet = mongo_cli.db.vets.find_one({'_id': vet_id})
            user = mongo_cli.db.users.find_one({'_id': vet['user_id']})
            mongo_cli.db.users.delete_one({'_id': user['_id']})
            mongo_cli.db.archived_users.insert_one(user)

        return {'deleted': bool(result.modified_count)}, 200


class Vets(Resource):
    def __init__(self):
        super().__init__()

        self._parser_get = reqparse.RequestParser()
        self._parser_get.add_argument('offset', type=int, default=0)
        self._parser_get.add_argument('limit', type=int, default=20)

        self._parser_post = reqparse.RequestParser()
        self._parser_post.add_argument('hospital_id', type=ObjectId)
        self._parser_post.add_argument('suffix')
        self._parser_post.add_argument('first_name', required=True)
        self._parser_post.add_argument('last_name', required=True)
        self._parser_post.add_argument('email_address', required=True)
        self._parser_post.add_argument('specialty')
        self._parser_post.add_argument('date_of_birth', type=strptime)
        self._parser_post.add_argument('dea')
        self._parser_post.add_argument('pims_id')
        self._parser_post.add_argument('gender')
        self._parser_post.add_argument('state_license')
        self._parser_post.add_argument('is_hospital_admin', required=True, type=bool)
        self._parser_post.add_argument('phone', required=True, type=FakeRequest)
        self._parser_post.add_argument('address', required=True, type=FakeRequest)

        self._parser_address = parser.address.copy()
        self._parser_phone = parser.phone.copy()

    def get(self):
        projection = {
            'suffix': True,
            'first_name': True,
            'last_name': True,
            'specialty': True,
            'image_url': True,
            'email_address': True,
            'phone': True,
            'state_license': True,
            'hospital_id': True,
            'address': True,
            'gender': True,
            'date_of_birth': True,
            'status': True,
            'dea': True,
            'pims_id': True
        }

        mongo_cli = MongoClient(host=MONGO_HOST)

        args = self._parser_get.parse_args()
        vets = list(mongo_cli.db.vets.find({'is_archived': {'$in': [None, False]}},
                                           projection=projection, skip=args['offset'], limit=args['limit']))

        vets_count = mongo_cli.db.vets.count({'is_archived': {'$in': [None, False]}})

        hospitals_cache = {}
        for vet in vets:
            vet['vet_id'] = vet.pop('_id')

            hid = vet['hospital_id']
            if hid not in hospitals_cache:
                hospital = mongo_cli.db.hospitals.find_one(
                    {'_id': hid},
                    projection={'name': True, '_id': False})
                hospitals_cache[hid] = hospital['name']
            vet['hospital_name'] = hospitals_cache[hid]

        return {'vets': vets, 'count': vets_count}, 200

    def post(self):
        args = self._parser_post.parse_args()
        args['phone'] = self._parser_phone.parse_args(req=args['phone'])
        args['address'] = self._parser_address.parse_args(req=args['address'])
        args['history'] = {'created_on': datetime.datetime.utcnow()}
        args['is_archived'] = False
        args['status'] = 'Pending'

        try:
            user_id, token = registration.register_user(args['email_address'], 'vet')
        except registration.TakenEmailError as e:
            return {'message': str(e)}, 400

        args['user_id'] = ObjectId(user_id)

        mongo_cli = MongoClient(host=MONGO_HOST)
        vet_id = mongo_cli.db.vets.insert_one(args).inserted_id

        confirmation = notification.send_confirmation(
            f"{args['first_name']} {args['last_name']}",
            args['email_address'], args['phone']['work'], token)

        return {'vet_id': vet_id, 'confirmation': confirmation}, 200
