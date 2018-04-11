import datetime

from bson.objectid import ObjectId
from flask_restful import Resource, reqparse
from pymongo import MongoClient

from app.common import notification
from app.common import parser
from app.common import registration
from app.common.env import *
from app.common.fake_request import FakeRequest
from app.common.types import strphone


class Pharmacy(Resource):
    def __init__(self):
        super().__init__()

        self._parser_put = reqparse.RequestParser()
        self._parser_put.add_argument('name')
        self._parser_put.add_argument('email')
        self._parser_put.add_argument('phone', type=strphone)
        self._parser_put.add_argument('fax')
        self._parser_put.add_argument('address', type=FakeRequest)
        self._parser_put.add_argument('type')

        self._parser_address = parser.address.copy()

    def get(self, pharmacy_id):
        projection = {
            'name': True,
            'email': True,
            'phone': True,
            'fax': True,
            'address': True,
            'type': True,
            'status': True,
            '_id': False
        }

        mongo_cli = MongoClient(host=MONGO_HOST)

        pharmacy = mongo_cli.db.pharmacies.find_one(
            {'_id': pharmacy_id, 'is_archived': {'$in': [None, False]}},
            projection=projection)

        if not pharmacy:
            return {}, 204

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

    def delete(self, pharmacy_id):
        mongo_cli = MongoClient(host=MONGO_HOST)

        result = mongo_cli.db.pharmacies.update_one({'_id': pharmacy_id},
                                                    {'$set': {
                                                        'is_archived': True,
                                                        'history.archived_on': datetime.datetime.utcnow()}})

        if result.modified_count:
            pharmacy = mongo_cli.db.pharmacies.find_one({'_id': pharmacy_id})
            user = mongo_cli.db.users.find_one({'_id': pharmacy['user_id']})
            mongo_cli.db.remove({'_id': user['_id']})
            mongo_cli.db.archived_users.insert_one(user)

        return {'deleted': bool(result.modified_count)}, 200


class Pharmacies(Resource):
    def __init__(self):
        super().__init__()

        self._parser_get = reqparse.RequestParser()
        self._parser_get.add_argument('offset', type=int, default=0)
        self._parser_get.add_argument('limit', type=int, default=20)

        self._parser_post = reqparse.RequestParser()
        self._parser_post.add_argument('name', required=True)
        self._parser_post.add_argument('email', required=True)
        self._parser_post.add_argument('phone', required=True, type=strphone)
        self._parser_post.add_argument('address', type=FakeRequest, required=True)
        self._parser_post.add_argument('type', required=True)

        self._parser_address = parser.address.copy()

    def get(self):
        projection = {
            'name': True,
            'email': True,
            'phone': True,
            'address': True,
            'status': True,
            'type': True
        }

        mongo_cli = MongoClient(host=MONGO_HOST)

        args = self._parser_get.parse_args()
        pharmacies = list(mongo_cli.db.pharmacies.find({'is_archived': {'$in': [None, False]}},
                                                       projection=projection, skip=args['offset'], limit=args['limit']))

        pharmacies_count = mongo_cli.db.pharmacies.count({'is_archived': {'$in': [None, False]}})

        for pharmacy in pharmacies:
            pharmacy['hospitals'] = list(mongo_cli.db.hospitals.find(
                {'$or': [
                    {'pharmacies.Retail': pharmacy['_id']},
                    {'pharmacies.Compounded': pharmacy['_id']},
                    {'pharmacies.502b': pharmacy['_id']}]},
                projection={'name': True, '_id': False}))

            pharmacy['pharmacy_id'] = pharmacy.pop('_id')

        return {'pharmacies': pharmacies, 'count': pharmacies_count}, 200

    def post(self):
        args = self._parser_post.parse_args()
        args['address'] = self._parser_address.parse_args(req=args['address'])
        args['history'] = {'created_on': datetime.datetime.utcnow()}
        args['is_archived'] = False
        args['status'] = 'Pending'

        try:
            user_id, token = registration.register_user(args['email'], 'pharmacy')
        except registration.TakenEmailError as e:
            return {'message': e}, 400

        args['user_id'] = ObjectId(user_id)

        mongo_cli = MongoClient(host=MONGO_HOST)
        pharmacy_id = mongo_cli.db.pharmacies.insert_one(args).inserted_id

        confirmation = notification.send_confirmation(
            args['name'], args['email'], args['phone'], token)

        return {'pharmacy_id': pharmacy_id, 'confirmation': confirmation}, 200
