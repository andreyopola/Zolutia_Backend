import requests
from flask_restful import Resource, reqparse

from app.common.env import *


class Register(Resource):
    def __init__(self):
        super().__init__()

        self._parser_post = reqparse.RequestParser()
        self._parser_post.add_argument('email', required=True)
        self._parser_post.add_argument('role', required=True)

    def post(self):
        args = self._parser_post.parse_args()

        url = '{}/api/v1/auth/register'.format(AUTH_HOST)
        resp = requests.post(url, json=args)

        return resp.json(), resp.status_code
