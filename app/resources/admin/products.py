import csv
import datetime

import boto3
from flask_restful import Resource, reqparse
from pymongo import MongoClient

from app.common import parser
from app.common.env import *
from app.common.fake_request import FakeRequest


class Product(Resource):
    def __init__(self):
        super().__init__()

        self._parser_put = reqparse.RequestParser()
        self._parser_put.add_argument('product_name')
        self._parser_put.add_argument('ndc')
        self._parser_put.add_argument('stc')
        self._parser_put.add_argument('description')
        self._parser_put.add_argument('type')
        self._parser_put.add_argument('category')
        self._parser_put.add_argument('manufacturer_name')
        self._parser_put.add_argument('image_url')
        self._parser_put.add_argument('available_options', action='append', type=FakeRequest)

        self._parser_options = parser.options.copy()

    def get(self, product_id):
        projection = {
            'history': False,
            'is_archived': False,
            '_id': False
        }

        mongo_cli = MongoClient(host=MONGO_HOST)

        product = mongo_cli.db.products.find_one(
            {
                '_id': product_id,
                'is_archived': {'$in': [None, False]}
            },
            projection=projection)

        if not product:
            return {}, 204

        return product, 200

    def put(self, product_id):
        args = {k: v for k, v in self._parser_put.parse_args().items() if v is not None}
        args['history.modified_on'] = datetime.datetime.utcnow()

        if 'available_options' in args:
            options = []
            for option in args['available_options']:
                options.append({k: v for k, v in
                                self._parser_options.parse_args(req=option).items() if v is not None})
            args['available_options'] = options

        mongo_cli = MongoClient(host=MONGO_HOST)

        result = mongo_cli.db.products.update_one({'_id': product_id}, {'$set': args})

        return {'updated': bool(result.modified_count)}, 200

    def delete(self, product_id):
        mongo_cli = MongoClient(host=MONGO_HOST)

        result = mongo_cli.db.products.update_one({'_id': product_id},
                                                  {'$set': {
                                                      'is_archived': True,
                                                      'history.archived_on': datetime.datetime.utcnow()}})

        return {'deleted': bool(result.modified_count)}, 200


class Products(Resource):
    def __init__(self):
        super().__init__()

        self._parser_get = reqparse.RequestParser()
        self._parser_get.add_argument('offset', type=int, default=0)
        self._parser_get.add_argument('limit', type=int, default=20)
        self._parser_get.add_argument('type')
        self._parser_get.add_argument('category')
        self._parser_get.add_argument('brand', action='append')

        self._parser_post = reqparse.RequestParser()
        self._parser_post.add_argument('product_name', required=True)
        self._parser_post.add_argument('ndc', required=True)
        self._parser_post.add_argument('stc', required=True)
        self._parser_post.add_argument('description', required=True)
        self._parser_post.add_argument('type', required=True)
        self._parser_post.add_argument('category', required=True)
        self._parser_post.add_argument('manufacturer_name', required=True)
        self._parser_post.add_argument('available_options', action='append',
                                       type=FakeRequest, required=True)

        self._parser_options = parser.options.copy()

    def get(self):
        projection = {
            'history': False,
            'is_archived': False,
            'ndc': False,
            'stc': False
        }

        mongo_cli = MongoClient(host=MONGO_HOST)

        args = {k: v for k, v in self._parser_get.parse_args().items() if v is not None}
        if args.get('brand') is not None:
            args['manufacturer_name'] = {'$in': args.pop('brand')}
        args['is_archived'] = {'$in': [None, False]}
        skip = args.pop('offset')
        limit = args.pop('limit')

        products = list(mongo_cli.db.products.find(args, projection=projection,
                                                   skip=skip, limit=limit, sort=[("product_name", 1)]))

        products_count = mongo_cli.db.products.count(args)
        brands = mongo_cli.db.products.distinct('manufacturer_name')
        categories = mongo_cli.db.products.distinct('category')

        for product in products:
            product['product_id'] = product.pop('_id')

        return {'products': products, 'count': products_count,
                'brands': brands, 'categories': categories}, 200

    def post(self):
        args = self._parser_post.parse_args()

        options = []
        for option in args['available_options']:
            options.append(self._parser_options.parse_args(req=option))
        args['available_options'] = options

        args['history'] = {'created_on': datetime.datetime.utcnow()}
        args['is_archived'] = False

        mongo_cli = MongoClient(host=MONGO_HOST)

        product_id = mongo_cli.db.products.insert_one(args).inserted_id

        return {'product_id': product_id}, 200


class Upload(Resource):
    def __init__(self):
        super().__init__()

        self._parser_post = reqparse.RequestParser()
        self._parser_post.add_argument('s3_file')

    def post(self):

        mongo_cli = MongoClient(host=MONGO_HOST)

        client = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY)
        local_file = 'products.csv'
        bucket_name = AWS_BUCKET_NAME
        dummy_imiage_url = 'https://images-na.ssl-images-amazon.com/images/I/4197CuIS0gL.jpg'

        args = self._parser_post.parse_args()
        s3_file = args['s3_file']

        if not s3_file.endswith('.csv'):
            return "File type is not csv"

        try:
            client.download_file(bucket_name, s3_file, local_file)
        except:
            return "File does not exist"

        with open(local_file, 'r') as f:

            reader = csv.reader(f, delimiter='\t')
            _ = next(reader, None)  # skip headers line
            if len(_) < 2:
                reader = csv.reader(f, delimiter=',')

            for row in reader:
                if len(row) < 10:
                    continue
                doc = dict()
                doc['available_options'] = list()
                options = dict()
                doc['ndc'] = row[0]
                doc['product_name'] = row[1].title()
                options['strength'] = row[2] if row[2] else "Generic"
                doc['image_url'] = dummy_imiage_url  # replace with "image_url_prefix + row[3]"
                doc['manufacturer_name'] = row[5]
                doc['type'] = 'OTC' if 'OTC' in row[7] else 'RX'
                doc['category'] = row[8]
                options['price'] = row[9]
                doc['available_options'].append(options)
                existing_prod = mongo_cli.db.products.find_one({"product_name": doc["product_name"],
                                                                "manufacturer_name": doc["manufacturer_name"]})
                existing_options = [item['strength'] for item in existing_prod['available_options']] if existing_prod \
                    else None
                if existing_prod and options['strength'] not in existing_options:
                    mongo_cli.db.products.update_one({"product_name": doc["product_name"],
                                                      "manufacturer_name": doc["manufacturer_name"]},
                                                     {"$push": {"available_options": options}})
                elif existing_prod:
                    mongo_cli.db.products.replace_one({"product_name": doc["product_name"],
                                                       "manufacturer_name": doc["manufacturer_name"]}, doc)
                elif not existing_prod:
                    mongo_cli.db.products.insert_one(doc)

        products = list(mongo_cli.db.products.find({}, projection={'available_options': True}))
        for product in products:
            product['product_id'] = product.pop('_id')

        hospitals = list(mongo_cli.db.hospitals.find({}, {}))

        for hospital in hospitals:
            _ = mongo_cli.db.hospitals.update_one({'_id': hospital['_id']}, {'$set': {'formulary': products}})

        return {}, 200
