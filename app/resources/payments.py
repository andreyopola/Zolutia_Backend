import datetime

import requests
from bson.objectid import ObjectId
from flask_restful import Resource, reqparse
from pymongo import MongoClient

from app.common import notification
from app.common.env import *

class Payments(Resource):
    def __init__(self):
        super().__init__()

        self._parser = reqparse.RequestParser()
        self._parser.add_argument('order_id', required='True', type=ObjectId)
        self._parser.add_argument('credit_card_name', required='True')
        self._parser.add_argument('credit_card_number', required='True')
        self._parser.add_argument('credit_card_expiry_month', required='True')
        self._parser.add_argument('credit_card_expiry_year', required='True')
        self._parser.add_argument('credit_card_cvv', required='True')

    def post(self):
        db = MongoClient(host=MONGO_HOST).db
        args = self._parser.parse_args()

        order = db.orders.find_one({'_id': args['order_id']})
        client = db.clients.find_one({'_id': order['client_id']})

        payment_endpoint = f"{PAYMENT_HOST}/api/v2/transactions"
        payload = args
        payload['order_id'] = str(payload['order_id'])
        resp = requests.post(payment_endpoint, json=payload)
        result = resp.json()
        status = {'result': result['message']}
        if resp.status_code :
            db.orders.update_one({'_id': args['order_id']}, {'$set': {
                'card_last4': args['credit_card_number'][-4:],
                'card_expiry': f"{args['credit_card_expiry_month']}/{args['credit_card_expiry_year']}",
                'order_status': 'processing',
                'cardholder_name': args['credit_card_name'],
                'reference_number': result['reference_number']}})

            if order['type'] == 'subscription':
                address = order['billing_address'] if 'billing_address' in order else order['shipping_address']
                if address:
                    address['firstName'] = client['first_name']
                    address['lastName'] = client['last_name']
                    address['email'] = client['email_address']
                    address['phone'] = client['phone']['cell']
                    address['street'] = address['street_1'] + ' ' + address['street_2']
                if args['credit_card_number'][0] == '3':
                    card_type = 'Amex'
                elif args['credit_card_number'][0] == '4':
                    card_type = 'Visa'
                elif args['credit_card_number'][0] == '5':
                    card_type = 'MasterCard'
                else:
                    card_type = 'Credit Card'
                card = {
                    'card_name': card_type,
                    'number': args['credit_card_number'],
                    'expiry_date': f"{args['credit_card_expiry_month']}/{args['credit_card_expiry_year']}",
                    'cvv': args['credit_card_cvv'],
                }
                payload = {
                    'address': address,
                    'credit_card': card,
                    'customer_number': str(order['client_id']),
                    'user': str(order['vet_id']),
                    'amount': order['total_price'],
                    'customer_id': str(order['client_id']),
                    'order_id': str(order['_id']),
                    'next': str(datetime.datetime.utcnow() + datetime.timedelta(days=90)),
                    'description': f"{client['first_name']} {client['last_name']} Order number {order['order_number']}"
                }
                r = requests.post(f"{PAYMENT_HOST}/api/v2/customers", json=payload,
                                  headers={'Content-Type': 'application/json'})
                if r.status_code == 200:
                    db.orders.update_one(
                        {'_id': order['_id']}, {'$set': {'customer_number': r.json().get('customer_code')}})
                    db.subscriptions.update_one(
                        {'_id': order['subscription_id']}, {'$set': {'customer_number': r.json().get('customer_code')}})

        return status, resp.status_code
