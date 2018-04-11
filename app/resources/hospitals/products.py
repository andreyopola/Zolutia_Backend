from flask_restful import Resource, reqparse, abort
from pymongo import MongoClient

from app.common.env import *


class Products(Resource):
    def __init__(self):
        self._parser_get = reqparse.RequestParser()
        self._parser_get.add_argument('type')
        self._parser_get.add_argument('category')
        self._parser_get.add_argument('brand', action='append')

    def get(self, hospital_id):
        mongo_cli = MongoClient(host=MONGO_HOST)

        projection = {
            "product_name": True,
            "image_url": True,
            "ndc": True,
            "stc": True,
            "description": True,
            "type": True,
            "category": True,
            "available_options": True,
            "manufacturer_name": True
        }

        results = []

        try:
            formulary = mongo_cli.db.hospitals.find_one(
                {
                    '_id': hospital_id,
                    'is_archived': {'$in': [False, None]}
                },
                projection={'_id': False, 'formulary.product_id': True}
            ).get('formulary')
        except:
            abort(400)

        args = {k: v for k, v in self._parser_get.parse_args().items() if v is not None}
        args['is_archived'] = {'$in': [False, None]}
        if args.get('brand') is not None:
            args['manufacturer_name'] = {'$in': args.pop('brand')}

        for p in formulary:
            args['_id'] = p['product_id']
            product = mongo_cli.db.products.find_one(args, projection=projection)
            if product:
                results.append(product)

        return {'products': results}, 200


class Product(Resource):
    def __init__(self):
        super().__init__()

        self._parser_put = reqparse.RequestParser()
        self._parser_put.add_argument('strength', required=True)
        self._parser_put.add_argument('retail_price', required=True, dest='price')

    def put(self, hospital_id, product_id):
        args = self._parser_put.parse_args()

        mongo_cli = MongoClient(host=MONGO_HOST)
        hospital = mongo_cli.db.hospitals.find_one(
            {'_id': hospital_id, 'is_archived': {'$in': [False, None]}})
        if hospital:
            try:
                formulary = hospital['formulary']
                for product in formulary:
                    if product['product_id'] == product_id:
                        for option in product['available_options']:
                            if option['strength'] == args['strength']:
                                option['price'] = args.pop('price')
                                break
                    if not args.get('price'):
                        break
            except TypeError:
                abort(400, message='Bad request')
            except KeyError:
                abort(400, message='Bad request')
        else:
            abort(400, message='Hospital not found')

        result = mongo_cli.db.hospitals.update_one(
            {'_id': hospital_id},
            {'$set': {'formulary': formulary}}
        )

        return {'updated': bool(result.modified_count)}, 200
