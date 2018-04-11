import requests

from app.common.env import *


class TakenEmailError(Exception):
    pass


def register_user(email, role):
    payload = {
        'email': email,
        'role': role
    }
    url = f'{AUTH_HOST}/api/v1/auth/register'

    resp = requests.post(url, json=payload)
    if resp.status_code != 200:
        raise TakenEmailError(resp.json().get('message'))

    return resp.json().get('user_id'), resp.json().get('token')
