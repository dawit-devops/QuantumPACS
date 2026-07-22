import jwt as _jwt
from jwt import PyJWTError


def encode(payload, key, algorithm='HS256'):
    token = _jwt.encode(payload, key, algorithm=algorithm)
    if isinstance(token, bytes):
        token = token.decode('utf-8')
    return token


def decode(token, key, algorithms=None):
    if algorithms is None:
        algorithms = ['HS256']
    return _jwt.decode(token, key, algorithms=algorithms)
