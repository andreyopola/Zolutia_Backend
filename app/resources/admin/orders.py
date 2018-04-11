import datetime

from bson.objectid import ObjectId
from flask_restful import Resource, reqparse
from pymongo import MongoClient

from app.common import parser
from app.common.datetime import strptime
from app.common.env import *
from app.common.fake_request import FakeRequest
from app.common import notification


class Order(Resource):
    def __init__(self):
        super().__init__()

        self._parser_put = reqparse.RequestParser()
        self._parser_put.add_argument('vet_id', type=ObjectId)
        self._parser_put.add_argument('client_id', type=ObjectId)
        self._parser_put.add_argument('patient_id', type=ObjectId)
        self._parser_put.add_argument('hospital_id', type=ObjectId)
        self._parser_put.add_argument('pharmacy_id', type=ObjectId)
        self._parser_put.add_argument('subscription_id', type=ObjectId)
        self._parser_put.add_argument('shipping_method')
        self._parser_put.add_argument('shipping_amount')
        self._parser_put.add_argument('shipping_date', type=strptime)
        self._parser_put.add_argument('delivered_date', type=strptime)
        self._parser_put.add_argument('tax')
        self._parser_put.add_argument('order_type')
        self._parser_put.add_argument('order_status')
        self._parser_put.add_argument('box_name')
        self._parser_put.add_argument('total_price')
        self._parser_put.add_argument('tracking_number')
        self._parser_put.add_argument('order_number', type=int)
        self._parser_put.add_argument('order_contents', type=FakeRequest, action='append')

        self._parser_order = parser.order.copy()

    def get(self, order_id):
        db = MongoClient(host=MONGO_HOST).db
        projection = {
            'history': False,
            'is_archived': False,
            '_id': False,
            'card': False
        }

        order = db.orders.find_one(
            {
                '_id': order_id
            },
            projection=projection)

        if not order:
            return {}, 204

        client = db.clients.find_one(
            {
                '_id': order['client_id'],
                'is_archived': {'$in': [None, False]}
            },
            projection={'first_name': True, 'last_name': True}) or {}
        order['client_name'] = '{} {}'.format(client.get('first_name'), client.get('last_name'))

        patient = db.patients.find_one(
            {
                '_id': order['patient_id'],
                'is_archived': {'$in': [None, False]}
            },
            projection={'name': True}) or {}
        order['patient_name'] = patient.get('name')

        vet = db.vets.find_one(
            {
                '_id': order['vet_id'],
                'is_archived': {'$in': [None, False]}
            },
            projection={'first_name': True, 'last_name': True}) or {}
        order['vet_name'] = '{} {}'.format(vet.get('first_name'), vet.get('last_name'))

        hospital = db.hospitals.find_one(
            {
                '_id': order['hospital_id'],
                'is_archived': {'$in': [None, False]}
            },
            projection={'name': True}) or {}
        order['hospital_name'] = hospital.get('name')

        pharmacy = db.pharmacies.find_one(
            {
                '_id': order['pharmacy_id'],
                'is_archived': {'$in': [None, False]}
            },
            projection={'name': True}) or {}
        order['pharmacy_name'] = pharmacy.get('name')

        for product in order['order_contents']:
            _ = db.products.find_one(
                {'_id': product['product_id']}) or {}
            product['product_name'] = _.get('product_name')
            product['image_url'] = _.get('image_url')
            product['type'] = _.get('type')

        return order, 200

    def put(self, order_id):
        db = MongoClient(host=MONGO_HOST).db
        args = {k: v for k, v in self._parser_put.parse_args().items() if v is not None}

        subtotal = 0.0
        order = db.orders.find_one({'_id': order_id})

        if 'order_contents' in args:
            for product in args['order_contents']:
                product = self._parser_order.parse_args(req=product)
                subtotal += float(product['product_price']) * int(product['quantity'])
        else:
            subtotal = float(order['subtotal_price'])

        total = subtotal + float(args.get('tax') or order['tax']) + float(
            args.get('shipping_amount') or order['shipping_amount'])

        args['subtotal_price'] = str(round(subtotal, 2))
        args['total_price'] = str(round(total, 2))

        args['history.modified_on'] = datetime.datetime.utcnow()

        result = db.orders.update_one({'_id': order_id}, {'$set': args})
        order_no = order.get('order_number', None)
        client_id = order.get('client_id', None)
        tracking_number = order.get('tracking_number', None)
        if client_id and order_no and tracking_number:
            notification.notify_client_shipping(client_id, order_no, tracking_number)

        return {'updated': bool(result.modified_count)}, 200

    def delete(self, order_id):
        db = MongoClient(host=MONGO_HOST).db

        result = db.orders.update_one({'_id': order_id},
                                      {'$set': {
                                          'is_archived': True,
                                          'history.archived_on': datetime.datetime.utcnow()}})

        return {'deleted': bool(result.modified_count)}, 200


class Orders(Resource):
    def __init__(self):
        super().__init__()

        self._parser_get = reqparse.RequestParser()
        self._parser_get.add_argument('offset', type=int, default=0)
        self._parser_get.add_argument('limit', type=int, default=20)

        self._parser_post = reqparse.RequestParser()
        self._parser_post.add_argument('vet_id', type=ObjectId, required=True)
        self._parser_post.add_argument('client_id', type=ObjectId, required=True)
        self._parser_post.add_argument('patient_id', type=ObjectId, required=True)
        self._parser_post.add_argument('hospital_id', type=ObjectId, required=True)
        self._parser_post.add_argument('pharmacy_id', type=ObjectId, required=True)
        self._parser_post.add_argument('subscription_id', type=ObjectId)
        self._parser_post.add_argument('shipping_method', required=True)
        self._parser_post.add_argument('shipping_amount', required=True)
        self._parser_post.add_argument('shipping_date', type=strptime)
        self._parser_post.add_argument('delivered_date', type=strptime)
        self._parser_post.add_argument('tax')
        self._parser_post.add_argument('order_type', required=True)
        self._parser_post.add_argument('box_name')
        self._parser_post.add_argument('total_price')
        self._parser_post.add_argument('tracking_number')
        self._parser_post.add_argument('order_number', type=int)
        self._parser_post.add_argument('order_contents', type=FakeRequest, action='append')

        self._parser_order = parser.order.copy()

    def get(self):
        db = MongoClient(host=MONGO_HOST).db
        projection = {
            'is_archived': False,
            'card': False,
            'order_contents': False,
            'shipping_name': False
        }

        args = self._parser_get.parse_args()
        orders = list(db.orders.find({'is_archived': {'$in': [None, False]}},
                                     projection=projection, skip=args['offset'], limit=args['limit']))

        orders_count = db.orders.count({'is_archived': {'$in': [None, False]}})

        for order in orders:
            order['order_id'] = order.pop('_id')
            order['order_date'] = order.pop('history')['created_on']
            if order['type'] == 'one_time':
                order['box_no'] = 0

            try:
                client = db.clients.find_one(
                    {
                        '_id': order['client_id'],
                    },
                    projection={
                        'first_name': True,
                        'last_name': True,
                        'email_address': True,
                        'phone': True})
                order['client_name'] = '{} {}'.format(client['first_name'], client['last_name'])
                order['email'] = client['email_address']
                order['phone'] = client['phone']['cell']
            except:
                pass

            try:
                patient = db.patients.find_one(
                    {
                        '_id': order['patient_id'],
                    },
                    projection={'name': True, 'birthday': True})
                order['patient_name'] = patient['name']
                order['date_of_birth'] = patient['birthday']
            except:
                pass

            try:
                vet = db.vets.find_one(
                    {
                        '_id': order['vet_id'],
                    },
                    projection={'first_name': True, 'last_name': True})
                order['vet_name'] = '{} {}'.format(vet['first_name'], vet['last_name'])
            except:
                pass

            try:
                hospital = db.hospitals.find_one(
                    {
                        '_id': order['hospital_id'],
                    },
                    projection={'name': True})
                order['hospital_name'] = hospital['name']
            except:
                pass

            try:
                pharmacy = db.pharmacies.find_one(
                    {
                        '_id': order['pharmacy_id'],
                    },
                    projection={'name': True})
                order['pharmacy_name'] = pharmacy['name']
            except:
                pass

        return {'orders': orders, 'count': orders_count}, 200

    def post(self):
        db = MongoClient(host=MONGO_HOST).db
        args = {k: v for k, v in self._parser_post.parse_args().items() if v is not None}

        subtotal = 0.0

        if 'order_contents' in args:
            for product in args['order_contents']:
                product = self._parser_order.parse_args(req=product)
                subtotal += float(product['product_price']) * float(product['quantity'])

        total = subtotal + float(args['tax']) + float(args['shipping_amount'])

        args['subtotal_price'] = str(round(subtotal, 2))
        args['total_price'] = str(round(total, 2))

        args['order_status'] = 'pending'

        args['history'] = {'created_on': datetime.datetime.utcnow()}
        args['is_archived'] = False

        order_id = db.orders.insert_one(args).inserted_id

        return {'order_id': order_id}, 200
