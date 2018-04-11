import datetime

from bson.objectid import ObjectId
from flask_restful import Resource, reqparse
from pymongo import MongoClient

from app.common.datetime import strptime
from app.common.env import *
from app.common.fake_request import FakeRequest


class TreatmentPlans(Resource):
    def __init__(self):
        super().__init__()

        self._parser_post_root = reqparse.RequestParser()
        self._parser_post_root.add_argument(
            'vet_id', required=True, type=ObjectId)
        self._parser_post_root.add_argument(
            'treatment_plan_name', required=True)
        self._parser_post_root.add_argument(
            'boxes', required=True, type=FakeRequest, action='append')

        self._parser_post_box = reqparse.RequestParser()
        self._parser_post_box.add_argument('box_price', required=True)
        self._parser_post_box.add_argument(
            'shipping_date', required=True, type=strptime)
        self._parser_post_box.add_argument('box_no', required=True)
        # self._parser_post_box.add_argument('box_id', required=True)
        self._parser_post_box.add_argument(
            'items', required=True, type=FakeRequest, action='append')

        self._parser_post_item = reqparse.RequestParser()
        self._parser_post_item.add_argument(
            'product_id', required=True, type=ObjectId)
        self._parser_post_item.add_argument('product_name', required=True)
        self._parser_post_item.add_argument('size', required=True)
        self._parser_post_item.add_argument(
            'quantity', required=True, type=int)
        self._parser_post_item.add_argument('instructions', required=True)
        self._parser_post_item.add_argument('notes', required=True)
        self._parser_post_item.add_argument('product_price', required=True)

        self._parser_put_root = reqparse.RequestParser()
        self._parser_put_root.add_argument('vet_id', type=ObjectId)
        self._parser_put_root.add_argument('treatment_plan_name')
        self._parser_put_root.add_argument(
            'boxes', type=FakeRequest, action='append')

        self._parser_put_box = reqparse.RequestParser()
        self._parser_put_box.add_argument('box_price')
        self._parser_put_box.add_argument('shipping_date', type=strptime)
        self._parser_put_box.add_argument('box_no')
        # self._parser_put_box.add_argument('box_id')
        self._parser_put_box.add_argument(
            'items', type=FakeRequest, action='append')

        self._parser_put_item = reqparse.RequestParser()
        self._parser_put_item.add_argument('product_id', type=ObjectId)
        self._parser_put_item.add_argument('product_name')
        self._parser_put_item.add_argument('size')
        self._parser_put_item.add_argument('quantity', type=int)
        self._parser_put_item.add_argument('instructions')
        self._parser_put_item.add_argument('notes')
        self._parser_put_item.add_argument('product_price')

    def get(self, vet_id, treatment_plan_id=None):
        mongo_cli = MongoClient(host=MONGO_HOST)

        projection = {
            "_id": True,
            "vet_id": True,
            "treatment_plan_name": True,
            "boxes": True,
            "last_modified": True,
        }

        if treatment_plan_id is None:
            vets_plans = mongo_cli.db.treatment_plans.find(
                {'vet_id': ObjectId(vet_id), 'is_archived': {
                    '$in': [False, None]}},
                projection=projection)

            results = [plan for plan in vets_plans]
            for result in results:
                result['plan_id'] = result.pop('_id')

            return {'results': results}, 200
        else:
            treatment_plan_id = ObjectId(treatment_plan_id)

            plan = mongo_cli.db.treatment_plans.find_one(
                {'vet_id': ObjectId(vet_id), '_id': treatment_plan_id, 'is_archived': {
                    '$in': [False, None]}},
                projection=projection)

            plan['plan_id'] = plan.pop('_id')

            for box in plan['boxes']:
                for product in box['items']:
                    _ = mongo_cli.db.products.find_one(
                        {'_id': product['product_id']})
                    product['image_url'] = _['image_url'] if _ else None
                    product['type'] = _['type'] if _ else None

            return plan, 200

    def post(self, vet_id):
        mongo_cli = MongoClient(host=MONGO_HOST)

        args = self._parser_post_root.parse_args()
        boxes = []
        for arg_box in args['boxes']:
            box = self._parser_post_box.parse_args(req=arg_box)
            items = []
            for arg_item in box['items']:
                item = self._parser_post_item.parse_args(req=arg_item)
                items.append(item)
            box['items'] = items
            boxes.append(box)
        args['boxes'] = boxes

        args['history'] = {
            'created_on': datetime.datetime.utcnow(),
            'modified_on': datetime.datetime.utcnow()
        }
        args['last_modified'] = datetime.datetime.utcnow()
        args['is_archived'] = False

        treatment_plan_id = mongo_cli.db.treatment_plans.insert_one(
            args).inserted_id
        _ = mongo_cli.db.vets.update_one({'_id': ObjectId(vet_id)},
                                         {'$push': {'treatment_plan_templates': treatment_plan_id}})

        return {'treatment_plan_id': treatment_plan_id}, 200

    def put(self, vet_id, treatment_plan_id):
        mongo_cli = MongoClient(host=MONGO_HOST)

        args = {k: v for k, v in self._parser_put_root.parse_args().items() if v is not None}
        args['last_modified'] = datetime.datetime.utcnow()
        args['history.modified_on'] = datetime.datetime.utcnow()

        if args.get('boxes'):
            boxes = []
            for arg_box in args['boxes']:
                box = self._parser_post_box.parse_args(req=arg_box)
                if box.get('items'):
                    items = []
                    for arg_item in box['items']:
                        item = self._parser_post_item.parse_args(req=arg_item)
                        items.append(item)
                    box['items'] = items
                    boxes.append(box)
            args['boxes'] = boxes

        result = mongo_cli.db.treatment_plans.update_one(
            {'_id': ObjectId(treatment_plan_id), 'vet_id': ObjectId(vet_id)},
            {'$set': args})

        return {'updated': bool(result.modified_count)}, 200

    def delete(self, vet_id, treatment_plan_id):
        mongo_cli = MongoClient(host=MONGO_HOST)

        _ = mongo_cli.db.vets.update_one({'_id': ObjectId(vet_id)},
                                         {'$pull': {'treatment_plan_templates': ObjectId(treatment_plan_id)}})

        result = mongo_cli.db.treatment_plans.update_one(
            {'_id': ObjectId(treatment_plan_id), 'vet_id': ObjectId(vet_id)},
            {'$set': {'is_archived': True, 'history.archived_on': datetime.datetime.utcnow()}})

        return {'deleted': bool(result.modified_count)}, 200
