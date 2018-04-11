from flask import Blueprint
from flask_restful import Api

from app.resources.hospitals import hospitals
from app.resources.hospitals import products
from app.resources.hospitals import vets

hospitals_bp = Blueprint('hospitals', __name__, url_prefix='/api/v1')
hospitals_api = Api(hospitals_bp, prefix='/hospitals')

hospitals_api.add_resource(hospitals.Hospital, '/<oid:hospital_id>')

hospitals_api.add_resource(products.Products, '/<oid:hospital_id>/products')
hospitals_api.add_resource(products.Product, '/<oid:hospital_id>/products/<oid:product_id>')

hospitals_api.add_resource(vets.Vets, '/<oid:hospital_id>/vets')
hospitals_api.add_resource(vets.Vet, '/<oid:hospital_id>/vets/<oid:vet_id>')
