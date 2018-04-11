import datetime

from bson.objectid import ObjectId
from flask_restful import Resource, abort, reqparse
from pymongo import MongoClient

from app.common import notification
from app.common import parser
from app.common import registration
from app.common.datetime import strptime
from app.common.env import *
from app.common.fake_request import FakeRequest


class Clients(Resource):
    def __init__(self):
        super().__init__()

        self._parser = reqparse.RequestParser()
        self._parser.add_argument('first_name', required=True)
        self._parser.add_argument('last_name', required=True)
        self._parser.add_argument('email_address', required=True)
        self._parser.add_argument('phone', required=True, type=FakeRequest)
        self._parser.add_argument('billing_address', type=FakeRequest)
        self._parser.add_argument('shipping_address', type=FakeRequest)

        self._parser_address = parser.address.copy()
        self._parser_phone = parser.phone.copy()

    def post(self):
        args = self._parser.parse_args()

        args['phone'] = {k: v for k, v in
                         self._parser_phone.parse_args(req=args['phone']).items() if v is not None}
        args['email_opt_out'] = False
        args['sms_opt_out'] = False
        args['history'] = {'created_on': datetime.datetime.utcnow()}
        args['status'] = 'Pending'
        args['is_archived'] = False

        if args.get('shipping_address') is not None:
            args['shipping_address'] = {k: v for k, v in
                                        self._parser_address.parse_args(req=args['shipping_address']).items()
                                        if v is not None}

        if args.get('billing_address') is not None:
            args['billing_address'] = {k: v for k, v in
                                       self._parser_address.parse_args(req=args['billing_address']).items()
                                       if v is not None}

        try:
            user_id, token = registration.register_user(args['email_address'], 'client')
        except registration.TakenEmailError as e:
            return {'message': str(e)}, 400

        args['user_id'] = ObjectId(user_id)

        mongo_cli = MongoClient(host=MONGO_HOST)
        client_id = mongo_cli.db.clients.insert_one(args).inserted_id

        confirmation = notification.send_confirmation(
            f"{args['first_name']} {args['last_name']}",
            args['email_address'], args['phone']['cell'], token)

        return {'client_id': client_id, 'confirmation': confirmation}, 200


class Client(Resource):
    def __init__(self):
        super().__init__()

        self._parser_put = reqparse.RequestParser()
        self._parser_put.add_argument('first_name')
        self._parser_put.add_argument('last_name')
        self._parser_put.add_argument('gender')
        self._parser_put.add_argument('image_url')
        self._parser_put.add_argument('date_of_birth', type=strptime)
        self._parser_put.add_argument('billing_address', type=FakeRequest)
        self._parser_put.add_argument('shipping_address', type=FakeRequest)
        # self._parser_put.add_argument('email_address')
        self._parser_put.add_argument('phone', type=FakeRequest)
        self._parser_put.add_argument('pets', type=list)
        self._parser_put.add_argument('email_opt_out', type=bool)
        self._parser_put.add_argument('sms_opt_out', type=bool)
        self._parser_put.add_argument('card', type=FakeRequest)

        self._parser_card = reqparse.RequestParser()
        self._parser_card.add_argument('number', required=True)
        self._parser_card.add_argument('expiry_date', required=True)
        self._parser_card.add_argument('cardholder_name', required=True)
        self._parser_card.add_argument('type')

        self._parser_address = parser.address.copy()
        self._parser_phone = parser.phone.copy()

    def get(self, client_id):
        projection = {
            '_id': False,
            'history': False,
            'is_archived': False
        }

        mongo_cli = MongoClient(host=MONGO_HOST)
        client = mongo_cli.db.clients.find_one(
            {'_id': client_id, 'is_archived': {'$in': [False, None]}},
            projection=projection)
        if not client:
            abort(404)

        sub_projection = {
            'patient_id': True,
            '_id': False
        }

        subs = mongo_cli.db.subscriptions.find(
            {'client_id': client_id,
             'subscription_status': 'Active'},
            projection=sub_projection)

        patient_ids = [sub['patient_id'] for sub in subs if 'patient_id' in sub]
        patients = list(mongo_cli.db.patients.find({'_id': {'$in': patient_ids}},
                                                   projection={'name': True, '_id': False}))
        for patient in patients:
            patient['patient_name'] = patient.pop('name')

        client['active_subscriptions'] = patients

        if 'shipping_address' not in client:
            order = mongo_cli.db.orders.find_one(
                {'client_id': client_id, 'is_archived': {'$in': [False, None]}}
            )
            if order:
                client['shipping_address'] = order['shipping_address']
            else:
                client['shipping_address'] = dict()

        if not client:
            abort(404, message='Not found')
        return client, 200

    def put(self, client_id):
        args = {k: v for k, v in self._parser_put.parse_args().items() if v is not None}
        if args.get('card') is not None:
            args['card'] = self._parser_card.parse_args(req=args['card'])[-4:]

        mongo_cli = MongoClient(host=MONGO_HOST)
        client = mongo_cli.db.clients.find_one({'_id': client_id})

        if args.get('shipping_address') is not None:
            shipping_address = self._parser_address.parse_args(req=args['shipping_address'])
            if client['shipping_address'] is not None:
                for k, v in shipping_address.items():
                    if v is not None:
                        args['shipping_address.{}'.format(k)] = v
                args.pop('shipping_address')

        if args.get('billing_address') is not None:
            billing_address = self._parser_address.parse_args(req=args['billing_address'])
            if client['billing_address'] is not None:
                for k, v in billing_address.items():
                    if v is not None:
                        args['billing_address.{}'.format(k)] = v
                args.pop('billing_address')

        if args.get('phone') is not None and not isinstance(args.get('phone'), str):
            for k, v in self._parser_phone.parse_args(req=args['phone']).items():
                if v is not None:
                    args['phone.{}'.format(k)] = v
            args.pop('phone')
        elif isinstance(args.get('phone'), str):
            args['phone'] = {"cell": args.get('phone')}

        args['history.modified_on'] = datetime.datetime.utcnow()

        result = mongo_cli.db.clients.update_one(
            {'_id': client_id}, {'$set': args})

        return {'updated': bool(result.modified_count)}, 200

    def delete(self, client_id):
        mongo_cli = MongoClient(host=MONGO_HOST)

        result = mongo_cli.db.clients.update_one({'_id': client_id},
                                                 {'$set': {
                                                     'is_archived': True,
                                                     'history.archived_on': datetime.datetime.utcnow()}})

        if result.modified_count:
            client = mongo_cli.db.clients.find_one({'_id': client_id})
            user = mongo_cli.db.users.find_one({'_id': client['user_id']})
            mongo_cli.db.remove({'_id': user['_id']})
            mongo_cli.db.archived_users.insert_one(user)

        return {'deleted': bool(result.modified_count)}, 200
