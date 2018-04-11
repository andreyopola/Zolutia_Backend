from flask import Blueprint
from flask_restful import Api

from app.resources.pharmacies import orders
from app.resources.pharmacies import pharmacies

pharmacies_bp = Blueprint('pharmacies', __name__, url_prefix='/api/v1')
pharmacies_api = Api(pharmacies_bp, prefix='/pharmacies')

pharmacies_api.add_resource(
    pharmacies.Pharmacy, '/<oid:pharmacy_id>')

pharmacies_api.add_resource(
    orders.Order, '/<oid:pharmacy_id>/orders/<oid:order_id>')
pharmacies_api.add_resource(
    orders.Orders, '/<oid:pharmacy_id>/orders')
