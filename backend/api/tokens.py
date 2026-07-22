"""Centralized JWT token creation and verification.
All auth flows must use this module to ensure consistent token format and expiry."""
from datetime import datetime, timedelta

from api.jwt_compat import encode as jwt_encode, decode as jwt_decode
from config import config


def create_token(user, expire=None):
    payload = {
        'id': user['id'],
        'admin': user['admin'],
    }
    if not expire:
        expire = {'days': 14}

    exp = datetime.utcnow() + timedelta(**expire)
    payload['exp'] = exp

    return jwt_encode(
        payload,
        config['secret'],
        algorithm='HS256',
    )


def verify_token(token):
    return jwt_decode(token, config['secret'])
