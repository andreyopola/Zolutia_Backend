import requests
from bson.objectid import ObjectId
from flask_restful import Resource, abort, reqparse
from pymongo import MongoClient

from app.common.env import *


class Registration(Resource):
    def __init__(self):
        super().__init__()

        self._parser = reqparse.RequestParser()
        self._parser.add_argument('type', required=True)
        self._parser.add_argument('client_id')

    def post(self):
        args = self._parser.parse_args()

        if args['type'] == 'client':
            mongo_cli = MongoClient(host=MONGO_HOST)

            client = mongo_cli.db.clients.find_one(
                {'_id': ObjectId(args['client_id'])})
            if client is None:
                abort(404, message='No such client')

            body = {
                'from_email': 'noreply@zolutia.com',
                'from_name': 'Zolutia',
                'to_email': client['email_address'],
                'to_name': f"{client['first_name']} {client['last_name']}",
                'subject': 'Zolutia registration',
                'template_id': '78787a0c-c7f1-4c15-81c2-0c10e42ae6ff',
                'substitutions': {
                    '{client}': f"{client['first_name']} {client['last_name']}",
                }
            }

            email_endpoint = NOTIFICATION_HOST + '/api/v1/notifications/emails'
            resp = requests.post(email_endpoint, json=body)
            email_sent = True if resp.status_code == 200 else False

            body = {
                'from': '+12018175749',
                'to': client['phone']['cell'],
                'message': 'Thanks for getting started with Zolutia!'
            }

            sms_endpoint = NOTIFICATION_HOST + '/api/v1/notifications/sms'
            resp = requests.post(sms_endpoint, data=body)
            sms_sent = True if resp.status_code == 200 else False
        else:
            email_sent = False
            sms_sent = False

        return {"email_sent": email_sent, "sms_sent": sms_sent}, 200


class Orders(Resource):
    def __init__(self):
        super().__init__()

        self._parser = reqparse.RequestParser()
        self._parser.add_argument('order_id', required=True)

    def post(self):
        args = self._parser.parse_args()

        mongo_cli = MongoClient(host=MONGO_HOST)

        order = mongo_cli.db.orders.find_one(
            {'_id': ObjectId(args['order_id'])})
        if order is None:
            abort(404, message='No such client')

        client = mongo_cli.db.clients.find_one({'_id': order['client_id']})

        body = {
            'from_email': 'sales@zolutia.com',
            'from_name': 'Zolutia',
            'to_email': client['email_address'],
            'to_name': f"{client['first_name']} {client['last_name']}",
            'subject': 'Order confirmation',
            'template_id': 'a885ecc0-396c-4297-ae5a-e73472a54668',
            'substitutions': {
                '{name}': f"{client['first_name']} {client['last_name']}",
                '{order}': str(order['order_number'])
            }
        }

        email_endpoint = NOTIFICATION_HOST + '/api/v1/notifications/emails'
        resp = requests.post(email_endpoint, json=body)
        email_sent = True if resp.status_code == 200 else False

        body = {
            'from': '+12018175749',
            'to': client['phone']['cell'],
            'message': 'Thanks for ordering from Zolutia!'
        }

        sms_endpoint = NOTIFICATION_HOST + '/api/v1/notifications/sms'
        resp = requests.post(sms_endpoint, data=body)
        sms_sent = True if resp.status_code == 200 else False

        return {"email_sent": email_sent, "sms_sent": sms_sent}, 200
