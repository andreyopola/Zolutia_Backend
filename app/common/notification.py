import requests
from flask import abort
from pymongo import MongoClient

from app.common.env import *

mongo_cli = MongoClient(host=MONGO_HOST, connect=False)


def send_confirmation(name, email, phone, token):
    confirm_link = f'{FRONTEND_URL}/confirm?token={token}'

    payload = {
        'from_email': 'noreply@zolutia.com',
        'from_name': 'Zolutia',
        'to_email': email,
        'to_name': name,
        'subject': 'Confirm Zolutia Registration',
        'template_id': CONFIRMATION_TEMPLATE,
        'substitutions': {
            '{link}': confirm_link,
            '{name}': name
        }
    }
    url = f'{NOTIFICATION_HOST}/api/v1/notifications/emails'
    email_resp = requests.post(url, json=payload)

    sms_text = f'Dear {name},You have been registered to Zolutia. Let’s get started. Click here to complete your ' \
               f'registration.{confirm_link} '
    payload = {
        'to': phone,
        'message': sms_text
    }
    url = f'{NOTIFICATION_HOST}/api/v1/notifications/sms'
    sms_resp = requests.post(url, json=payload)

    resp = {
        'email': 'sent' if email_resp.status_code == 200 else email_resp.json(),
        'sms': 'sent' if sms_resp.status_code == 200 else sms_resp.json(),
    }

    return resp, 200


def notify_pharmacy_order(pharmacy_id, order_no):
    pharmacy = mongo_cli.db.pharmacies.find_one({'_id': pharmacy_id})

    body = {
        'from_email': 'noreply@zolutia.com',
        'from_name': 'Zolutia',
        'to_email': pharmacy['email'],
        'to_name': pharmacy['name'],
        'subject': 'New order in Zolutia',
        'template_id': ORDER_PHARMACY_TEMPLATE,
        'substitutions': {
            '{name}': pharmacy['name'],
            '{order_no}': str(order_no),
        }
    }
    url = f'{NOTIFICATION_HOST}/api/v1/notifications/emails'
    email_resp = requests.post(url, json=body)

    sms_text = f"Dear {pharmacy['name']}, you have a new order no{order_no} in Zolutia. For more details, log in."
    payload = {
        'to': pharmacy['phone'],
        'message': sms_text
    }
    url = f'{NOTIFICATION_HOST}/api/v1/notifications/sms'
    sms_resp = requests.post(url, json=payload)

    resp = {
        'email': 'sent' if email_resp.status_code == 200 else email_resp.json(),
        'sms': 'sent' if sms_resp.status_code == 200 else sms_resp.json(),
    }

    return resp, 200


def notify_client_order(client_id, order_no):
    client = mongo_cli.db.clients.find_one({'_id': client_id})

    body = {
        'from_email': 'sales@zolutia.com',
        'from_name': 'Zolutia',
        'to_email': client['email_address'],
        'to_name': f"{client['first_name']} {client['last_name']}",
        'subject': 'Order confirmation',
        'template_id': ORDER_CLIENT_TEMPLATE,
        'substitutions': {
            '{name}': f"{client['first_name']} {client['last_name']}",
            '{order}': str(order_no)
        }
    }
    url = f'{NOTIFICATION_HOST}/api/v1/notifications/emails'
    email_resp = requests.post(url, json=body)
    client_name = f"{client['first_name']} {client['last_name']}"

    sms_text = f"Dear {client_name}, you have a new order no{order_no} in Zolutia. For more details, log in."
    payload = {
        'to': client['phone']['cell'],
        'message': sms_text
    }
    url = f'{NOTIFICATION_HOST}/api/v1/notifications/sms'
    sms_resp = requests.post(url, json=payload)

    resp = {
        'email': 'sent' if email_resp.status_code == 200 else email_resp.json(),
        'sms': 'sent' if sms_resp.status_code == 200 else sms_resp.json(),
    }

    return resp, 200


def notify_client_shipping(client_id, order_no, tracking_no):
    client = mongo_cli.db.clients.find_one({'_id': client_id})

    body = {
        'from_email': 'sales@zolutia.com',
        'from_name': 'Zolutia',
        'to_email': client['email_address'],
        'to_name': f"{client['first_name']} {client['last_name']}",
        'subject': 'Your Zolutia Box has Shipped',
        'template_id': SHIPPING_CLIENT_TEMPLATE,
        'substitutions': {
            '{name}': f"{client['first_name']} {client['last_name']}",
            '{order_no}': str(order_no),
            '{tracking}': str(tracking_no)
        }
    }
    url = f'{NOTIFICATION_HOST}/api/v1/notifications/emails'
    email_resp = requests.post(url, json=body)
    client_name = f"{client['first_name']} {client['last_name']}"

    sms_text = f"Hello {client_name}, Your Zolutia Box for order no{order_no} has been shipped! Please click " \
               f"here to login and  access your account where you can track your order"
    payload = {
        'to': client['phone']['cell'],
        'message': sms_text
    }
    url = f'{NOTIFICATION_HOST}/api/v1/notifications/sms'
    sms_resp = requests.post(url, json=payload)

    resp = {
        'email': 'sent' if email_resp.status_code == 200 else email_resp.json(),
        'sms': 'sent' if sms_resp.status_code == 200 else sms_resp.json(),
    }

    return resp, 200


def notify_client_subscription(client_id, order_date):
    client = mongo_cli.db.clients.find_one({'_id': client_id})
    client_name = f"{client['first_name']} {client['last_name']}"

    body = {
        'from_email': 'sales@zolutia.com',
        'from_name': 'Zolutia',
        'to_email': client['email_address'],
        'to_name': client_name,
        'subject': 'Your Auto Fulfillment Program Has Started',
        'template_id': SUBSCRIPTION_CLIENT_TEMPLATE,
        'substitutions': {
            '{order_date}': str(order_date.strftime('%Y-%m-%d')),
        }
    }
    url = f'{NOTIFICATION_HOST}/api/v1/notifications/emails'
    email_resp = requests.post(url, json=body)

    sms_text = "Your first Care Plan order is being processed! Access your account here www.Zolutia.com."
    payload = {
        'to': client['phone']['cell'],
        'message': sms_text
    }
    url = f'{NOTIFICATION_HOST}/api/v1/notifications/sms'
    sms_resp = requests.post(url, json=payload)

    resp = {
        'email': 'sent' if email_resp.status_code == 200 else email_resp.json(),
        'sms': 'sent' if sms_resp.status_code == 200 else sms_resp.json(),
    }

    return resp, 200


def notify_forgot_password(email, token):
    user = mongo_cli.db.users.find_one({'email_address': email})
    if not user:
        abort(400)
    elif user['role'] == 'vet':
        vet = mongo_cli.db.vets.find_one({'user_id': user['_id']})
        if not vet:
            abort(400)
        user['name'] = f"{vet['first_name']} {vet['last_name']}"
        user['phone'] = vet['phone']['work']
    elif user['role'] == 'pharmacy':
        pharmacy = mongo_cli.db.pharmacies.find_one({'user_id': user['_id']})
        if not pharmacy:
            abort(400)
        user['name'] = pharmacy['name']
        user['phone'] = pharmacy['phone']
    elif user['role'] == 'client':
        client = mongo_cli.db.client.find_one({'user_id': user['_id']})
        if not client:
            abort(400)
        user['name'] = f"{client['first_name']} {client['last_name']}"
        user['name'] = client['phone']['cell']

    confirm_link = f'{FRONTEND_URL}/reset?token={token}'  # TODO
    body = {
        'from_email': 'noreply@zolutia.com',
        'from_name': 'Zolutia',
        'to_email': user['email_address'],
        'to_name': user['name'],
        'subject': 'Reset Zolutia Password',
        'template_id': RESET_PASSWORD_TEMPLATE,
        'substitutions': {
            '{link}': confirm_link,
        }
    }
    url = f'{NOTIFICATION_HOST}/api/v1/notifications/emails'
    email_resp = requests.post(url, json=body)

    sms_text = f"We’ve received a request to reset your password. " \
               f"Click here to reset your Zolutia password: {confirm_link}."
    payload = {
        'to': user['phone'],
        'message': sms_text
    }
    url = f'{NOTIFICATION_HOST}/api/v1/notifications/sms'
    sms_resp = requests.post(url, json=payload)

    resp = {
        'email': 'sent' if email_resp.status_code == 200 else email_resp.json(),
        'sms': 'sent' if sms_resp.status_code == 200 else sms_resp.json(),
    }

    return resp, 200


def notify_successful_registration(token):
    user = mongo_cli.db.users.find_one({'confirmation_token': token})
    if not user:
        abort(400)
    elif user['role'] == 'vet':
        vet = mongo_cli.db.vets.find_one({'user_id': user['_id']})
        if not vet:
            abort(400)
        user['name'] = f"{vet['first_name']} {vet['last_name']}"
        user['phone'] = vet['phone']['work']
    elif user['role'] == 'pharmacy':
        pharmacy = mongo_cli.db.pharmacies.find_one({'user_id': user['_id']})
        if not pharmacy:
            abort(400)
        user['name'] = pharmacy['name']
        user['phone'] = pharmacy['phone']
    elif user['role'] == 'client':
        client = mongo_cli.db.clients.find_one({'user_id': user['_id']})
        if not client:
            abort(400)
        user['name'] = f"{client['first_name']} {client['last_name']}"
        user['phone'] = client['phone']['cell']

    body = {
        'from_email': 'noreply@zolutia.com',
        'from_name': 'Zolutia',
        'to_email': user['email_address'],
        'to_name': user['name'],
        'subject': 'Welcome to Zolutia!',
        'template_id': WELCOME_TEMPLATE,
    }
    url = f'{NOTIFICATION_HOST}/api/v1/notifications/emails'
    email_resp = requests.post(url, json=body)

    sms_text = 'Welcome to Zolutia! Access your new account here: www.Zolutia.com'
    payload = {
        'to': user['phone'],
        'message': sms_text
    }
    url = f'{NOTIFICATION_HOST}/api/v1/notifications/sms'
    sms_resp = requests.post(url, json=payload)

    resp = {
        'email': 'sent' if email_resp.status_code == 200 else email_resp.json(),
        'sms': 'sent' if sms_resp.status_code == 200 else sms_resp.json(),
    }

    return resp, 200
