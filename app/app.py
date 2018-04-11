from flask import Flask
from flask_cors import CORS
from flask_restful import Api

from app.common.json import MongoEncoder, MongoDecoder
from app.common.url_map import ObjectIdConverter
from app.resources import notifications
from app.resources import patients
from app.resources import payments
from app.resources import users
from app.resources.admin import admin_bp
from app.resources.clients import clients_bp
from app.resources.hospitals import hospitals_bp
from app.resources.orders import orders_bp
from app.resources.pharmacies import pharmacies_bp
from app.resources.vets import vets_bp

app = Flask(__name__)
app.json_encoder = MongoEncoder
app.json_decoder = MongoDecoder
app.config['RESTFUL_JSON'] = {
    'separators': (', ', ': '),
    'indent': 2,
    'cls': MongoEncoder
}
app.url_map.converters['object_id'] = ObjectIdConverter
app.url_map.converters['oid'] = ObjectIdConverter

CORS(app)

api = Api(app, prefix='/api/v1')

app.register_blueprint(admin_bp)

app.register_blueprint(clients_bp)

app.register_blueprint(hospitals_bp)

api.add_resource(notifications.Orders, '/notifications/orders', endpoint='notifications_orders')
api.add_resource(notifications.Registration, '/notifications/registration')

app.register_blueprint(orders_bp)

api.add_resource(patients.Patients, '/patients')

api.add_resource(payments.Payments, '/payments')

app.register_blueprint(pharmacies_bp)

api.add_resource(users.CheckToken, '/users/check_token')
api.add_resource(users.Confirm, '/users/confirm')
api.add_resource(users.Forgot, '/users/forgot')
api.add_resource(users.Login, '/users/login')
api.add_resource(users.Reset, '/users/reset')

app.register_blueprint(vets_bp)
