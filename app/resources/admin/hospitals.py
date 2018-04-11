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
        self._parser_put.add_argument('email')
        self._parser_put.add_argument('phone', type=strphone)
        self._parser_put.add_argument('fax')
        self._parser_put.add_argument('address', type=FakeRequest)
        self._parser_put.add_argument('formulary', type=FakeRequest, action='append')
        self._parser_put.add_argument('pharmacies', type=FakeRequest)
        self._parser_put.add_argument('pims_id')
        self._parser_put.add_argument('clinic_id')
        self._parser_put.add_argument('owner_name')
        self._parser_put.add_argument('parent_account')

        self._parser_address = parser.address.copy()
        self._parser_formulary = parser.formulary.copy()
        self._parser_options = parser.options.copy()
        self._parser_pharmacies = parser.pharmacies.copy()

    def get(self, hospital_id):
        db = MongoClient(host=MONGO_HOST).db
        projection = {
            'name': True,
            'email': True,
            'phone': True,
            'fax': True,
            'address': True,
            'pharmacies': True,
            'owner_name': True,
            'clinic_id': True,
            'pims_id': True,
            'parent_account': True,
            'status': True,
            '_id': False,
        }

        hospital = db.hospitals.find_one(
            {
                '_id': hospital_id,
                'is_archived': {'$in': [None, False]}
            },
            projection=projection)

        if not hospital:
            return {}, 204

        if 'pharmacies' in hospital:
            for pharmacy_type, pharmacy_id in dict(hospital['pharmacies']).items():
                pharmacy = db.pharmacies.find_one(
                    {'_id': pharmacy_id}, projection={'name': True})
                hospital['pharmacies'][f'{pharmacy_type}_name'] = pharmacy['name']

        return hospital, 200

    def put(self, hospital_id):
        db = MongoClient(host=MONGO_HOST).db
        args = {k: v for k, v in self._parser_put.parse_args().items() if v is not None}

        if 'address' in args:
            args['address'] = {k: v for k, v in
                               self._parser_address.parse_args(req=args['address']).items() if v is not None}

        if 'formulary' in args:
            products = []
            for product in args['formulary']:
                p = self._parser_formulary.parse_args(req=product)
                if 'available_options' in p:
                    options = []
                    for option in p['available_options']:
                        o = self._parser_options.parse_args(req=option)
                        options.append(o)
                    p['available_options'] = options
                products.append(p)
            args['formulary'] = products

        if 'pharmacies' in args:
            for k, v in self._parser_pharmacies.parse_args(req=args['pharmacies']).items():
                if v is not None:
                    args[f'pharmacies.{k}'] = v
            args.pop('pharmacies')

        args['history.modified_on'] = datetime.datetime.utcnow()

        result = db.hospitals.update_one({'_id': hospital_id}, {'$set': args})

        return {'updated': bool(result.modified_count)}, 200

    def delete(self, hospital_id):
        db = MongoClient(host=MONGO_HOST).db

        result = db.hospitals.update_one({'_id': hospital_id},
                                         {'$set': {
                                             'is_archived': True,
                                             'history.archived_on': datetime.datetime.utcnow()}})

        if result.modified_count:
            hospital = db.hospitals.find_one({'_id': hospital_id})
            user = db.users.find_one({'_id': hospital['user_id']})
            db.remove({'_id': user['_id']})
            db.archived_users.insert_one(user)

        return {'deleted': bool(result.modified_count)}, 200


class Hospitals(Resource):
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
        self._parser_post.add_argument('formulary', type=FakeRequest, action='append')
        self._parser_post.add_argument('pharmacies', type=FakeRequest)
        self._parser_post.add_argument('pims_id')
        self._parser_post.add_argument('clinic_id')
        self._parser_post.add_argument('owner_name')
        self._parser_post.add_argument('parent_account')

        self._parser_address = parser.address.copy()
        self._parser_formulary = parser.formulary.copy()
        self._parser_options = parser.options.copy()
        self._parser_pharmacies = parser.pharmacies.copy()

    def get(self):
        db = MongoClient(host=MONGO_HOST).db
        projection = {
            'name': True,
            'email': True,
            'phone': True,
            'fax': True,
            'address': True,
            'parent_name': True,
            'clinic_id': True,
            'pims_id': True,
            'pharmacies': True,
            'owner_name': True,
            'parent_account': True,
            'status': True,
        }

        args = self._parser_get.parse_args()
        hospitals = list(db.hospitals.find({'is_archived': {'$in': [None, False]}},
                                           projection=projection, skip=args['offset'], limit=args['limit']))

        hospitals_count = db.hospitals.count()

        for hospital in hospitals:
            hospital['hospital_id'] = hospital.pop('_id')
            if 'pharmacies' in hospital:
                for pharmacy_type, pharmacy_id in dict(hospital['pharmacies']).items():
                    pharmacy = db.pharmacies.find_one(
                        {'_id': pharmacy_id}, projection={'name': True})
                    if pharmacy:
                        hospital['pharmacies'][f'{pharmacy_type}_name'] = pharmacy['name']

        return {'hospitals': hospitals, 'count': hospitals_count}, 200

    def post(self):
        db = MongoClient(host=MONGO_HOST).db
        args = self._parser_post.parse_args()

        # try:
        #     user_id, token = registration.register_user(args['email'], 'hospital')
        # except registration.TakenEmailError as e:
        #     return {'message': e}, 400

        # args['user_id'] = ObjectId(user_id)

        args['address'] = self._parser_address.parse_args(req=args['address'])

        if 'pharmacies' in args:
            pharmacies = {k: v for k, v in
                          self._parser_pharmacies.parse_args(req=args['pharmacies']).items()
                          if v is not None}
            args['pharmacies'] = pharmacies

        products = []
        if 'formulary' in args and args['formulary']:
            for product in args['formulary']:
                p = self._parser_formulary.parse_args(req=product)
                options = []
                for option in p['available_options']:
                    o = self._parser_options.parse_args(req=option)
                    options.append(o)
                p['available_options'] = options
                products.append(p)
            args['formulary'] = products
        else:
            products = list(db.products.find({}, projection={'available_options': True}))
            for product in products:
                product['product_id'] = product.pop('_id')
                product['margin'] = '10%'
            args['formulary'] = products

        args['history'] = {'created_on': datetime.datetime.utcnow()}
        args['is_archived'] = False
        args['status'] = 'Pending'

        hospital_id = db.hospitals.insert_one(args).inserted_id

        # confirmation = notification.send_confirmation(
        #     args['name'], args['email'], args['phone'], token)

        return {'hospital_id': hospital_id}, 200
