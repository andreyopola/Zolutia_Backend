from flask import Blueprint
from flask_restful import Api

from app.resources.admin import hospitals
from app.resources.admin import orders
from app.resources.admin import patients
from app.resources.admin import pharmacies
from app.resources.admin import products
from app.resources.admin import users
from app.resources.admin import vets

admin_bp = Blueprint('admin', __name__, url_prefix='/api/v1')
admin_api = Api(admin_bp, prefix='/admin')

admin_api.add_resource(hospitals.Hospitals, '/hospitals')
admin_api.add_resource(hospitals.Hospital, '/hospitals/<oid:hospital_id>')

admin_api.add_resource(orders.Orders, '/orders')
admin_api.add_resource(orders.Order, '/orders/<oid:order_id>')

admin_api.add_resource(patients.Patients, '/patients')
admin_api.add_resource(patients.Patient, '/patients/<oid:patient_id>')

admin_api.add_resource(pharmacies.Pharmacies, '/pharmacies')
admin_api.add_resource(pharmacies.Pharmacy, '/pharmacies/<oid:pharmacy_id>')

admin_api.add_resource(products.Products, '/products')
admin_api.add_resource(products.Product, '/products/<oid:product_id>')
admin_api.add_resource(products.Upload, '/upload')

admin_api.add_resource(vets.Vets, '/vets')
admin_api.add_resource(vets.Vet, '/vets/<oid:vet_id>')

admin_api.add_resource(users.Register, '/register')
