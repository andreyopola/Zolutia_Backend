import datetime
from base64 import b64encode

import requests
from bson import ObjectId
from flask_restful import Resource, abort, reqparse
from pymongo import MongoClient

from app.common import notification
from app.common.env import *

mongo_cli = MongoClient(host=MONGO_HOST, connect=False)


def basic_auth(login, password):
    b64 = b64encode('{}:{}'.format(login, password).encode('UTF-8'))
    return 'Basic {}'.format(b64.decode('UTF-8'))


class Login(Resource):
    def __init__(self):
        super().__init__()

        self._get_parser = reqparse.RequestParser()
        self._get_parser.add_argument('login', required=True, type=str.lower)
        self._get_parser.add_argument('password', required=True)

    def post(self):
        args = self._get_parser.parse_args()

        headers = {'Authorization': basic_auth(args['login'], args['password'])}
        r = requests.get('{}/api/v1/auth/login'.format(AUTH_HOST), headers=headers)

        if r.status_code != 200:
            abort(403, message='Invalid credentials')

        response = r.json()

        if response['role'] == 'vet':
            vet = mongo_cli.db.vets.find_one({'user_id': ObjectId(response['user_id'])})
            if vet:
                response['vet_id'] = vet['_id']
                response['name'] = '{} {}'.format(vet['first_name'], vet['last_name'])
                return response, 200

        elif response['role'] == 'client':
            client = mongo_cli.db.clients.find_one({'user_id': ObjectId(response['user_id'])})
            if client:
                response['client_id'] = client['_id']
                response['name'] = '{} {}'.format(client['first_name'], client['last_name'])
                return response, 200

        elif response['role'] == 'pharmacy':
            pharmacy = mongo_cli.db.pharmacies.find_one({'user_id': ObjectId(response['user_id'])})
            if pharmacy:
                response['pharmacy_id'] = pharmacy['_id']
                response['name'] = pharmacy['name']
                return response, 200

        elif response['role'] == 'admin':
            response['name'] = 'Zolutia Admin'
            return response, 200

        abort(500, message='Internal DB error')


class Reset(Resource):
    def __init__(self):
        super().__init__()

        self._get_parser = reqparse.RequestParser()
        self._get_parser.add_argument('login', required=True)
        self._get_parser.add_argument('password', required=True)
        self._get_parser.add_argument('new_password', required=True)

    def put(self):
        args = self._get_parser.parse_args()

        headers = {
            'Authorization': basic_auth(args['login'], args['password']),
            'Zol-New-Password': b64encode(args['new_password'].encode('UTF-8')).decode('UTF-8')
        }
        r = requests.put(
            '{}/api/v1/auth/reset'.format(AUTH_HOST), headers=headers)

        if r.status_code == 200:
            response = r.json()
            return response, 200

        abort(403, message='Invalid credentials')


class Confirm(Resource):
    def __init__(self):
        super().__init__()

        self._parser_post = reqparse.RequestParser()
        self._parser_post.add_argument('token', required=True)
        self._parser_post.add_argument('password', required=True)

    def post(self):
        args = self._parser_post.parse_args()

        url = '{}/api/v1/auth/confirm'.format(AUTH_HOST)
        resp = requests.post(url, json=args)

        if resp.status_code == 200 and resp.json()['confirmed'] is True:
            notification.notify_successful_registration(args['token'])

        return resp.json(), resp.status_code


class CheckToken(Resource):
    def __init__(self):
        super().__init__()

        self._parser_get = reqparse.RequestParser()
        self._parser_get.add_argument('token', required=True)

    def get(self):
        args = self._parser_get.parse_args()

        user = mongo_cli.db.users.find_one({
            '$or': [
                {'confirmation_token': args['token']},
                {'forgot_token': args['token']}
            ]})

        if not user:
            abort(400, message='Token is invalid or expired')

        response = {'user_id': user['_id'], 'role': user['role']}

        if user['role'] == 'vet':
            vet = mongo_cli.db.vets.find_one({'user_id': user['_id']})
            if vet:
                response['vet_id'] = vet['_id']
                response['name'] = f"{vet['first_name']} {vet['last_name']}"
                response['email'] = vet['email_address']

        elif user['role'] == 'pharmacy':
            pharmacy = mongo_cli.db.pharmacies.find_one({'user_id': user['_id']})
            if pharmacy:
                response['pharmacy_id'] = pharmacy['_id']
                response['name'] = pharmacy['name']
                response['email'] = pharmacy['email']

        elif user['role'] == 'client':
            client = mongo_cli.db.clients.find_one({'user_id': user['_id']})
            if client:
                response['client_id'] = client['_id']
                response['name'] = f"{client['first_name']} {client['last_name']}"
                response['email'] = client['email_address']

        return response, 200


class Forgot(Resource):
    def __init__(self):
        super().__init__()
        self._parser_get = reqparse.RequestParser()
        self._parser_get.add_argument('email', required=True, dest='email_address')

        self._parser_post = reqparse.RequestParser()
        self._parser_post.add_argument('token', required=True)
        self._parser_post.add_argument('password', required=True)

    def get(self):
        args = self._parser_get.parse_args()
        r = requests.get(f'{AUTH_HOST}/api/v1/auth/forgotpassword', data=args)

        if r.status_code == 200:
            notification.notify_forgot_password(args['email_address'], r.json()['token'])
            return {'notification': 'sent'}, 200

        return r.json(), r.status_code

    def post(self):
        args = self._parser_post.parse_args()

        user = mongo_cli.db.users.find_one({'forgot_token': args['token']})
        if not user:
            abort(400, message='Invalid token')
        args['email_address'] = user['email_address']
        args['password_text'] = args.pop('password')
        headers = {
            'Content-Type': 'application/json'
        }
        r = requests.post(f'{AUTH_HOST}/api/v1/auth/forgotpassword', json=args, headers=headers)
        return r.json(), r.status_code
