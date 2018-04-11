import datetime

from bson.objectid import ObjectId
from flask_restful import Resource, reqparse
from pymongo import MongoClient

from app.common.datetime import strptime
from app.common.env import *
from app.common.fake_request import FakeRequest


class Patients(Resource):
    def __init__(self):
        super().__init__()

        self._parser_root = reqparse.RequestParser()
        self._parser_root.add_argument(
            'patients', required=True, type=dict, action='append')

        self._parser_patients = reqparse.RequestParser()
        self._parser_patients.add_argument('name', required=True)
        self._parser_patients.add_argument(
            'client_id', required=True, type=ObjectId)
        self._parser_patients.add_argument(
            'vet_id', required=True, type=ObjectId)
        self._parser_patients.add_argument(
            'hospital_id', required=True, type=ObjectId)
        self._parser_patients.add_argument('species', required=True)
        self._parser_patients.add_argument('breed', required=True)
        self._parser_patients.add_argument('age', required=True)
        self._parser_patients.add_argument(
            'birthday', required=True, type=strptime)
        self._parser_patients.add_argument('weight', required=True)
        self._parser_patients.add_argument('gender', required=True)

    def post(self):
        db = MongoClient(host=MONGO_HOST).db
        root_args = self._parser_root.parse_args()
        args = []

        for arg in root_args['patients']:
            patient = self._parser_patients.parse_args(req=FakeRequest(arg))
            patient['history'] = {
                'created_on': datetime.datetime.now(),
                'modified_on': datetime.datetime.now()
            }
            patient['is_archived'] = False

            args.append(patient)

        resp = db.patients.insert_many(args)

        return {'inserted': True if len(resp.inserted_ids) > 0 else False}, 200
