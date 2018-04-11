import datetime

from bson.objectid import ObjectId
from flask_restful import Resource, abort, reqparse
from pymongo import MongoClient

from app.common import notification
from app.common.datetime import strptime
from app.common.env import *
from app.common.fake_request import FakeRequest

mongo_cli = MongoClient(host=MONGO_HOST, connect=False)


class Orders(Resource):
    def __init__(self):
        super().__init__()

        self._parser_post = reqparse.RequestParser()
        self._parser_post.add_argument('vet_id', required=True, type=ObjectId)
        self._parser_post.add_argument('client_id', required=True, type=ObjectId)
        self._parser_post.add_argument('patient_id', required=True, type=ObjectId)
        self._parser_post.add_argument('hospital_id', required=True, type=ObjectId)
        self._parser_post.add_argument('treatment_plan_id', type=ObjectId)
        self._parser_post.add_argument('order_contents', type=FakeRequest, action='append')
        self._parser_post.add_argument('subtotal_price')
        self._parser_post.add_argument('shipping_method', required=True)
        self._parser_post.add_argument('shipping_amount', required=True)
        self._parser_post.add_argument('shipping_address', required=True, type=FakeRequest)
        self._parser_post.add_argument('tax', required=True)
        self._parser_post.add_argument('total_price')
        self._parser_post.add_argument(
            'order_type', required=False, default='one_time',
            choices=('one_time', 'subscription',), dest='type')

        self._parser_content = reqparse.RequestParser()
        self._parser_content.add_argument('product_id', required=True, type=ObjectId)
        self._parser_content.add_argument('strength', required=True)
        self._parser_content.add_argument('instructions')
        self._parser_content.add_argument('quantity', required=True, type=int)
        self._parser_content.add_argument('expires', required=True, type=strptime)
        self._parser_content.add_argument('auto_refill', required=True, type=bool)
        self._parser_content.add_argument('refills', required=True, type=int)

        self._parser_address = reqparse.RequestParser()
        self._parser_address.add_argument('street_1', required=True)
        self._parser_address.add_argument('street_2')
        self._parser_address.add_argument('city', required=True)
        self._parser_address.add_argument('state', required=True)
        self._parser_address.add_argument('zip', required=True)
        self._parser_address.add_argument('zip4', required=True)

    def post(self):
        args = self._parser_post.parse_args()

        if args['type'] == 'subscription':
            if 'treatment_plan_id' not in args:
                abort(400, message='Missing treatment_plan_id for subscription order')

            plan = mongo_cli.db.treatment_plans.find_one(
                {'_id': args['treatment_plan_id'], 'is_archived': {'$in': [None, False]}})
            if not plan:
                abort(400, message='Treatment plan not found')

            first_box = plan['boxes'][0]

            subscription = {
                'vet_id': args['vet_id'],
                'client_id': args['client_id'],
                'patient_id': args['patient_id'],
                'hospital_id': args['hospital_id'],
                'subscription_status': 'Active',
                'is_archived': False,
                'history': {'created_on': datetime.datetime.utcnow()},
                'treatment_plan_id': args['treatment_plan_id'],
                'boxes': plan['boxes'],
                'upcoming_box_no': plan['boxes'][min(1, len(plan['boxes']) - 1)]['box_no'],
                'upcoming_shipment_date': datetime.datetime.utcnow() + datetime.timedelta(days=90),
            }

            future_boxes = []
            for box in plan['boxes'][2:]:
                if len(future_boxes) == 3:
                    break
                date = future_boxes[-1]['shipment_date'] \
                    if future_boxes else subscription['upcoming_shipment_date']
                date += datetime.timedelta(days=90)
                future_boxes.append(
                    {'box_no': box['box_no'], 'shipment_date': date})

            last_box = plan['boxes'][-1]
            while len(future_boxes) < 3:
                date = future_boxes[-1]['shipment_date'] \
                    if future_boxes else subscription['upcoming_shipment_date']
                date += datetime.timedelta(days=90)
                future_boxes.append(
                    {'box_no': last_box['box_no'], 'shipment_date': date})

            subscription['future_boxes'] = future_boxes

            sub_id = mongo_cli.db.subscriptions.insert_one(subscription).inserted_id
            args['subscription_id'] = sub_id
            args['order_contents'] = first_box['items']
        elif args.get('order_contents'):

            args['order_contents'] = [self._parser_content.parse_args(req=c)
                                      for c in args['order_contents']]

        else:
            abort(400, message='Missing order_contents for one time order')

        subtotal = 0.0
        for p in args['order_contents']:
            pipeline = [  # wtf i've done
                {'$match': {'_id': args['hospital_id']}},
                {'$unwind': '$formulary'},
                {'$match': {'formulary.product_id': p['product_id']}},
                {'$unwind': '$formulary.available_options'},
                {'$match': {'formulary.available_options.strength': p.get('strength', p.get('size'))}}
            ]

            try:
                product = list(mongo_cli.db.hospitals.aggregate(pipeline))[0]
            except BaseException:
                abort(400, message='Bad request')
            p['product_price'] = product['formulary']['available_options']['price']
            subtotal += float(p['product_price']) * int(p['quantity'])
            total = subtotal + float(args['tax']) + float(args['shipping_amount'])

            args['subtotal_price'] = str(round(subtotal, 2))
            args['total_price'] = str(round(total, 2))

        product_types = set()
        for p in args['order_contents']:
            product = mongo_cli.db.products.find_one({'_id': p['product_id']})
            product_types.add(product['type'].lower())

        if {'otc'} == product_types:
            args['pharmacy_type'] = 'OTC'
        elif '502b' in product_types:
            args['pharmacy_type'] = '502b'
        elif 'compounded' in product_types:
            args['pharmacy_type'] = 'Compounded'
        else:
            args['pharmacy_type'] = 'Retail'

        hospital = mongo_cli.db.hospitals.find_one(
            {'_id': args['hospital_id']}, projection={'pharmacies': True})

        if args['pharmacy_type'] != 'OTC':
            args['pharmacy_id'] = hospital['pharmacies'][args['pharmacy_type']]
        else:
            args['pharmacy_id'] = None

        args['shipping_address'] = self._parser_address.parse_args(req=args['shipping_address'])

        args['history'] = {
            'created_on': datetime.datetime.utcnow(),
        }

        args['order_number'] = 100001

        last_order = mongo_cli.db.orders.find_one({}, sort=[('order_number', -1)])
        if last_order:
            args['order_number'] = last_order['order_number'] + 1

        args['order_status'] = 'pending'
        args['shipping_date'] = datetime.datetime.utcnow() + datetime.timedelta(days=4)
        args['delivery_date'] = None
        args['tracking_number'] = None
        args['tracking_status'] = None
        args['box_no'] = '1'

        order_id = mongo_cli.db.orders.insert_one(args).inserted_id

        if args['pharmacy_id']:
            confirmation = notification.notify_pharmacy_order(
                args['pharmacy_id'], args['order_number'])
        else:
            confirmation = False

        notification.notify_client_order(args['client_id'], args['order_number'])

        order = {
            'order_id': order_id,
            'order_number': args['order_number'],
            'shipping_date': args['shipping_date'],
            'confirmation': confirmation
        }

        client = mongo_cli.db.clients.find_one({'_id': args['client_id']})
        order['client_name'] = '{} {}'.format(client['first_name'], client['last_name'])
        patient = mongo_cli.db.patients.find_one({'_id': args['patient_id']})
        order['patient_name'] = patient['name']

        if args['type'] == 'subscription':
            notification.notify_client_subscription(args['client_id'], order['shipping_date'])

        return order, 200
