from flask import Blueprint
from flask_restful import Api

from app.resources.vets import clients
from app.resources.vets import orders
from app.resources.vets import patients
from app.resources.vets import products
from app.resources.vets import search
from app.resources.vets import treatment_plans
from app.resources.vets import vets

vets_bp = Blueprint('vets', __name__, url_prefix='/api/v1')
vets_api = Api(vets_bp, prefix='/vets')

vets_api.add_resource(clients.Clients, '/<oid:vet_id>/clients/<oid:client_id>')

vets_api.add_resource(orders.Orders, '/<oid:vet_id>/orders')
vets_api.add_resource(orders.Order, '/<oid:vet_id>/orders/<oid:order_id>')
vets_api.add_resource(orders.Feedbacks, '/<oid:vet_id>/feedbacks')
vets_api.add_resource(orders.Feedback, '/<oid:vet_id>/feedbacks/<oid:order_id>')

vets_api.add_resource(
    patients.Patients, '/<oid:vet_id>/patients')
vets_api.add_resource(
    patients.PatientOrders, '/<oid:vet_id>/patients/<oid:patient_id>/orders')
vets_api.add_resource(
    patients.PatientSearch, '/<oid:vet_id>/patients/search')

vets_api.add_resource(products.Products, '/<oid:vet_id>/products')
vets_api.add_resource(products.MultipleProducts, '/<oid:vet_id>/multiple_products')
vets_api.add_resource(products.Product, '/<oid:vet_id>/products/<oid:product_id>')

vets_api.add_resource(search.Search, '/<oid:vet_id>/search')

vets_api.add_resource(
    treatment_plans.TreatmentPlans, '/<oid:vet_id>/treatment_plans', endpoint='vets_tp')
vets_api.add_resource(
    treatment_plans.TreatmentPlans, '/<oid:vet_id>/treatment_plans/<oid:treatment_plan_id>')

vets_api.add_resource(vets.Vets, '', endpoint='get_vet')
vets_api.add_resource(vets.Vets, '/<oid:vet_id>')
