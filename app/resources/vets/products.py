from bson.objectid import ObjectId
from flask_restful import Resource, abort, reqparse
from pymongo import MongoClient

from app.common.env import *


class Products(Resource):
    def __init__(self):
        self._parser_get = reqparse.RequestParser()
        self._parser_get.add_argument('offset', type=int, default=0)
        self._parser_get.add_argument('limit', type=int, default=20)
        self._parser_get.add_argument('type')
        self._parser_get.add_argument('ids')
        self._parser_get.add_argument('category')
        self._parser_get.add_argument('brand', action='append')

    def get(self, vet_id):
        mongo_cli = MongoClient(host=MONGO_HOST)

        vet = mongo_cli.db.vets.find_one({'_id': vet_id, 'is_archived': {'$in': [False, None]}})
        if vet is None:
            abort(404, message='No such vet')

        hospital_id = vet['hospital_id']
        if hospital_id is None:
            abort(500, message='Vet\'s data is incorrect')

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

        args = {k: v for k, v in self._parser_get.parse_args().items() if v is not None}
        skip = args.pop('offset')
        limit = args.pop('limit')

        if 'ids' in args:
            product_ids = args['ids'].split(';')

            hospital = mongo_cli.db.hospitals.find_one({'_id': hospital_id})

            projection = {
                "product_name": True,
                "image_url": True,
                "ndc": True,
                "stc": True,
                "description": True,
                "type": True,
                "category": True,
                "manufacturer_name": True
            }

            products = list()
            for product_id in product_ids:
                product = mongo_cli.db.products.find_one(
                    {
                        '_id': ObjectId(product_id),
                        'is_archived': {'$in': [False, None]}
                    },
                    projection=projection)

                product['product_id'] = product.pop('_id')

                for prod in hospital['formulary']:
                    if prod['product_id'] == product['product_id']:
                        product['available_options'] = prod['available_options']

                products.append(product)

            return {'products': products}, 200

        try:
            formulary = mongo_cli.db.hospitals.find_one(
                {'_id': hospital_id, 'is_archived': {'$in': [False, None]}},
                projection={'formulary.product_id': True,
                            'formulary.available_options': True}).get('formulary')
        except AttributeError:
            abort(404, message='Hospital not found')

        if not formulary:
            return {'results': [], 'count': 0}

        product_ids = [_['product_id'] for _ in formulary]
        available_options = {item['product_id']: item['available_options'] for item in formulary}
        brands = mongo_cli.db.products.distinct('manufacturer_name', {'_id': {'$in': product_ids}})
        categories = mongo_cli.db.products.distinct('category', {'_id': {'$in': product_ids}})
        args['_id'] = {'$in': product_ids}
        args['is_archived'] = {'$in': [False, None]}

        if args.get('brand') is not None:
            args['manufacturer_name'] = {'$in': args.pop('brand')}

        formulary_count = mongo_cli.db.products.count(args)
        products = list(mongo_cli.db.products.find(args, projection=projection,
                                                   skip=skip, limit=limit, sort=[("product_name", 1)]))

        for item in products:
            item['available_options'] = available_options[item['_id']]

        return {'results': products, 'count': formulary_count,
                'brands': brands, 'categories': categories}, 200


class Product(Resource):
    def get(self, vet_id, product_id):
        mongo_cli = MongoClient(host=MONGO_HOST)

        vet = mongo_cli.db.vets.find_one({'_id': vet_id, 'is_archived': {'$in': [False, None]}})
        if vet is None:
            abort(404, message='No such vet')

        hospital_id = vet['hospital_id']
        if hospital_id is None:
            abort(500, message='Vet\'s data is incorrect')
        else:
            hospital = mongo_cli.db.hospitals.find_one({'_id': hospital_id})

        projection = {
            "product_name": True,
            "image_url": True,
            "ndc": True,
            "stc": True,
            "description": True,
            "type": True,
            "category": True,
            "manufacturer_name": True
        }

        if mongo_cli.db.hospitals.count({
            '_id': hospital_id,
            'formulary.product_id': product_id}) == 0:
            return {}, 200

        product = mongo_cli.db.products.find_one(
            {
                '_id': ObjectId(product_id),
                'is_archived': {'$in': [False, None]}
            },
            projection=projection)

        for prod in hospital['formulary']:
            if prod['product_id'] == product['_id']:
                product['available_options'] = prod['available_options']

        product['product_id'] = product.pop('_id')

        return product, 200


class MultipleProducts(Resource):
    def __init__(self):
        self._parser_get = reqparse.RequestParser()
        self._parser_get.add_argument('ids', required=True)

    def get(self, vet_id):
        mongo_cli = MongoClient(host=MONGO_HOST)
        args = self._parser_get.parse_args()
        product_ids = []
        if 'ids' in args:
            product_ids = args['ids'].split(';')
        else:
            abort(404, message='Pass list of product ids')

        vet = mongo_cli.db.vets.find_one({'_id': vet_id, 'is_archived': {'$in': [False, None]}})
        if vet is None:
            abort(404, message='No such vet')

        hospital_id = vet['hospital_id']
        if hospital_id is None:
            abort(500, message='Vet\'s data is incorrect')
        else:
            hospital = mongo_cli.db.hospitals.find_one({'_id': hospital_id})

        projection = {
            "product_name": True,
            "image_url": True,
            "ndc": True,
            "stc": True,
            "description": True,
            "type": True,
            "category": True,
            "manufacturer_name": True
        }
        #
        # if mongo_cli.db.hospitals.count({
        #     '_id': hospital_id,
        #         'formulary.product_id': {'$in': product_ids}}) == 0:
        #     return {}, 200

        products = list()
        for product_id in product_ids:
            product = mongo_cli.db.products.find_one(
                {
                    '_id': ObjectId(product_id),
                    'is_archived': {'$in': [False, None]}
                },
                projection=projection)

            product['product_id'] = product.pop('_id')

            for prod in hospital['formulary']:
                if prod['product_id'] == product['product_id']:
                    product['available_options'] = prod['available_options']

            products.append(product)

        return {'products': products}, 200
