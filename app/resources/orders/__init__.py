from flask import Blueprint
from flask_restful import Api

from app.resources.orders import orders

orders_bp = Blueprint('orders', __name__, url_prefix='/api/v1')
orders_api = Api(orders_bp, prefix='/orders')

orders_api.add_resource(orders.Orders, '')
