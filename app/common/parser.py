from bson.objectid import ObjectId
from flask_restful import reqparse

from app.common.datetime import strptime
from app.common.fake_request import FakeRequest
from app.common.types import strphone

address = reqparse.RequestParser()
address.add_argument('street_1')
address.add_argument('street_2')
address.add_argument('city')
address.add_argument('state')
address.add_argument('zip')
address.add_argument('zip4')

phone = reqparse.RequestParser()
phone.add_argument('cell', type=strphone)
phone.add_argument('work', type=strphone)

formulary = reqparse.RequestParser()
formulary.add_argument('product_id', type=ObjectId)
formulary.add_argument('margin')
formulary.add_argument('available_options', type=FakeRequest, action='append')

options = reqparse.RequestParser()
options.add_argument('strength')
options.add_argument('price')

order = reqparse.RequestParser()
order.add_argument('auto_refill')
order.add_argument('expires', type=strptime)
order.add_argument('quantity')
order.add_argument('instructions')
order.add_argument('refills')
order.add_argument('product_price')
order.add_argument('strength')
order.add_argument('product_id', type=ObjectId)

pharmacies = reqparse.RequestParser()
pharmacies.add_argument('Retail', type=ObjectId)
pharmacies.add_argument('Compounded', type=ObjectId)
pharmacies.add_argument('502b', type=ObjectId)
