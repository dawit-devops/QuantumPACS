from datetime import datetime, timedelta, timezone

from api.jwt_compat import encode as jwt_encode, decode as jwt_decode
from config import config


def create_token(user, expire=None):
    payload = {
        'id': user['id'],
        'admin': user['admin'],
    }
    if not expire:
        expire = {'days': 14}

    exp = datetime.now(timezone.utc) + timedelta(**expire)
    payload['exp'] = exp

    return jwt_encode(
        payload,
        config['secret'],
        algorithm='HS256',
    )


def verify_token(token):
    return jwt_decode(token, config['secret'])
