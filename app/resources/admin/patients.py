import datetime

from bson.objectid import ObjectId
from flask_restful import Resource, reqparse
from pymongo import MongoClient

from app.common import parser, notification, registration
from app.common.datetime import strptime
from app.common.env import *
from app.common.fake_request import FakeRequest

class Patient(Resource):
    def __init__(self):
        super().__init__()

        self._parser_put = reqparse.RequestParser()
        self._parser_put.add_argument('client_id', type=ObjectId)
        self._parser_put.add_argument('hospital_id', type=ObjectId)
        self._parser_put.add_argument('vet_id', type=ObjectId)
        self._parser_put.add_argument('name')
        self._parser_put.add_argument('species')
        self._parser_put.add_argument('breed')
        self._parser_put.add_argument('gender')
        self._parser_put.add_argument('age')
        self._parser_put.add_argument('birthday', type=strptime)
        self._parser_put.add_argument('weight')
        self._parser_put.add_argument('first_name')
        self._parser_put.add_argument('last_name')
        self._parser_put.add_argument('phone', type=FakeRequest)
        self._parser_put.add_argument('shipping_address', type=FakeRequest)
        self._parser_put.add_argument('billing_address', type=FakeRequest)

        self._parser_address = parser.address.copy()
        self._parser_phone = parser.phone.copy()

    def get(self, patient_id):
        db = MongoClient(host=MONGO_HOST).db
        projection = {
            'history': False,
            'is_archived': False,
            '_id': False
        }

        patient = db.patients.find_one(
            {
                '_id': patient_id,
                'is_archived': {'$in': [None, False]}
            },
            projection=projection)

        if not patient:
            return {}, 204

        client = db.clients.find_one(
            {
                '_id': patient['client_id'],
                'is_archived': {'$in': [None, False]}
            },
            projection={
                'first_name': True,
                'last_name': True,
                'email_address': True,
                'shipping_address': True,
                'phone': True})
        patient['client_name'] = '{} {}'.format(client['first_name'], client['last_name'])
        patient['email'] = client['email_address']
        patient['phone'] = client['phone']
        patient['shipping_address'] = client['shipping_address']

        vet = db.vets.find_one(
            {
                '_id': patient['vet_id'],
                'is_archived': {'$in': [None, False]}
            },
            projection={
                'suffix': True,
                'first_name': True,
                'last_name': True})
        patient['vet_name'] = ""
        if vet:
            patient['vet_name'] = f"{vet['suffix']} {vet['first_name']} {vet['last_name']}"

        hospital = db.hospitals.find_one(
            {
                '_id': patient['hospital_id'],
                'is_archived': {'$in': [None, False]}
            },
            projection={'name': True})
        patient['hospital_name'] = ""
        if hospital:
            patient['hospital_name'] = hospital.get('name', "")

        return patient, 200

    def put(self, patient_id):
        db = MongoClient(host=MONGO_HOST).db
        args = {k: v for k, v in self._parser_put.parse_args().items() if v is not None}
        if 'phone' in args:
            args['phone'] = {k: v for k, v in
                             self._parser_phone.parse_args(req=args['phone']).items()
                             if v is not None}
        if args.get('shipping_address') is not None:
            args['shipping_address'] = {k: v for k, v in
                                        self._parser_address.parse_args(req=args['shipping_address']).items()
                                        if v is not None}

        if args.get('billing_address') is not None:
            args['billing_address'] = {k: v for k, v in
                                       self._parser_address.parse_args(req=args['billing_address']).items()
                                       if v is not None}
        client_keys = ['first_name', 'last_name', 'email_address', 'phone', 'billing_address',
                       'shipping_address', 'history.modified_on']
        patient_keys = ['name', 'species', 'breed', 'gender', 'age', 'weight', 'birthday',
                        'client_id', 'hospital_id', 'vet_id', 'history.modified_on']
        args['history.modified_on'] = datetime.datetime.utcnow()

        client = {k: args.get(k) for k in client_keys if args.get(k) is not None}
        patient = {k: args.get(k) for k in patient_keys if args.get(k) is not None}

        args['history.modified_on'] = datetime.datetime.utcnow()

        if client:
            client_result = db.clients.update_one(
                {'_id': patient['client_id']}, {'$set': client}).modified_count
        else:
            client_result = False

        if patient:
            patient_result = db.patients.update_one(
                {'_id': patient_id}, {'$set': patient}).modified_count
        else:
            patient_result = False

        return {'client_updated': bool(client_result),
                'patient_updated': bool(patient_result)}, 200

    def delete(self, patient_id):
        db = MongoClient(host=MONGO_HOST).db
        result = db.patients.update_one({'_id': patient_id},
                                        {'$set': {
                                            'is_archived': True,
                                            'history.archived_on': datetime.datetime.utcnow()}})

        return {'deleted': bool(result.modified_count)}, 200


class Patients(Resource):
    def __init__(self):
        super().__init__()

        self._parser_get = reqparse.RequestParser()
        self._parser_get.add_argument('offset', type=int, default=0)
        self._parser_get.add_argument('limit', type=int, default=20)

        self._parser_post = reqparse.RequestParser()
        self._parser_post.add_argument('client_id', type=ObjectId)
        self._parser_post.add_argument('hospital_id', type=ObjectId)
        self._parser_post.add_argument('vet_id', type=ObjectId)
        self._parser_post.add_argument('first_name', required=True)
        self._parser_post.add_argument('last_name', required=True)
        self._parser_post.add_argument('email_address', required=True)
        self._parser_post.add_argument('phone', required=True, type=FakeRequest)
        self._parser_post.add_argument('shipping_address', type=FakeRequest)
        self._parser_post.add_argument('billing_address', type=FakeRequest)
        self._parser_post.add_argument('name', required=True)
        self._parser_post.add_argument('species', required=True)
        self._parser_post.add_argument('breed', required=True)
        self._parser_post.add_argument('gender', required=True)
        self._parser_post.add_argument('age', required=True)
        self._parser_post.add_argument('birthday', type=strptime, required=True)
        self._parser_post.add_argument('weight', required=True)

        self._parser_address = parser.address.copy()
        self._parser_phone = parser.phone.copy()

    def get(self):
        db = MongoClient(host=MONGO_HOST).db
        projection = {
            'history': False,
            'is_archived': False,
            'age': False
        }

        args = self._parser_get.parse_args()

        patients = list(db.patients.find({'is_archived': {'$in': [None, False]}},
                                         projection=projection, skip=args['offset'], limit=args['limit']))

        patients_count = db.patients.count({'is_archived': {'$in': [None, False]}})

        for patient in patients:
            patient['patient_id'] = patient.pop('_id')

            client = db.clients.find_one(
                {
                    '_id': patient['client_id'],
                },
                projection={'first_name': True, 'last_name': True})
            patient['client_name'] = '{} {}'.format(client['first_name'], client['last_name'])

            vet = db.vets.find_one(
                {
                    '_id': patient['vet_id'],
                },
                projection={
                    'suffix': True,
                    'first_name': True,
                    'last_name': True})
            if vet:
                patient['vet_name'] = f"{vet['suffix']} {vet['first_name']} {vet['last_name']}"
            else:
                patient['vet_name'] = ""

            hospital = db.hospitals.find_one(
                {
                    '_id': patient['hospital_id'],
                },
                projection={'name': True})
            if hospital:
                patient['hospital_name'] = hospital.get('name', "")
            else:
                patient['hospital_name'] = ""

        return {'patients': patients, 'count': patients_count}, 200

    def post(self):
        db = MongoClient(host=MONGO_HOST).db
        args = self._parser_post.parse_args()
        args['phone'] = {k: v for k, v in
                         self._parser_phone.parse_args(req=args['phone']).items() if v is not None}
        if args.get('shipping_address') is not None:
            args['shipping_address'] = {k: v for k, v in
                                        self._parser_address.parse_args(req=args['shipping_address']).items()
                                        if v is not None}

        if args.get('billing_address') is not None:
            args['billing_address'] = {k: v for k, v in
                                       self._parser_address.parse_args(req=args['billing_address']).items()
                                       if v is not None}

        args['history'] = {'created_on': datetime.datetime.utcnow()}
        args['is_archived'] = False

        client_keys = ['first_name', 'last_name', 'email_address', 'phone', 'billing_address', 'shipping_address',
                       'history', 'is_archived']
        patient_keys = ['name', 'species', 'breed', 'gender', 'age', 'weight', 'birthday', 'client_id', 'hospital_id',
                        'vet_id', 'history', 'is_archived']

        client = {k: args.get(k, None) for k in client_keys}
        patient = {k: args.get(k, None) for k in patient_keys}
        try:
            user_id, token = registration.register_user(client['email_address'], 'client')
        except registration.TakenEmailError as e:
            return {'message': str(e)}, 400

        confirmation = notification.send_confirmation(
            f"{client['first_name']} {client['last_name']}",
            client['email_address'], client['phone']['cell'], token)

        client['user_id'] = ObjectId(user_id)
        client_id = db.clients.insert_one(client).inserted_id

        patient['client_id'] = client_id
        patient_id = db.patients.insert_one(patient).inserted_id

        return {'patient_id': patient_id, 'client_id': client_id, 'confirmation': confirmation}, 200
