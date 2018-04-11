from flask import Blueprint
from flask_restful import Api

from app.resources.clients import care_team
from app.resources.clients import clients
from app.resources.clients import orders
from app.resources.clients import patients
from app.resources.clients import payments

# from app.resources.clients import subscriptions


clients_bp = Blueprint('clients', __name__, url_prefix='/api/v1')
clients_api = Api(clients_bp, prefix='/clients')

clients_api.add_resource(care_team.CareTeam, '/<oid:client_id>/care_team')

clients_api.add_resource(clients.Client, '/<oid:client_id>')
clients_api.add_resource(clients.Clients, '')

clients_api.add_resource(
    orders.Order, '/<oid:client_id>/orders/<oid:order_id>')
clients_api.add_resource(
    orders.Orders, '/<oid:client_id>/orders')

clients_api.add_resource(
    patients.Patient, '/<oid:client_id>/patients/<oid:patient_id>')
clients_api.add_resource(
    patients.Patients, '/<oid:client_id>/patients')

clients_api.add_resource(payments.Payments, '/<oid:client_id>/payments')

# clients_api.add_resource(
#     subscriptions.Subscription, '/<oid:client_id>/subscriptions/<oid:subscription_id>')
# clients_api.add_resource(
#     subscriptions.Subscriptions, '/<oid:client_id>/subscriptions')
