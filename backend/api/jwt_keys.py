"""RSA signing-key management for RS256 tokens (R2-10/11).

Access/refresh tokens are minted with RS256 and the public key is published
via the OIDC JWKS endpoint (``/api/oauth/jwks``) so the discovery document's
``jwks_uri`` is real and verifiable. The private key lives in a PEM file that
is auto-generated on first use; it must be protected like the app secret and
rotated only with a coordinated JWKS rollout (old keys stay accepted for the
rotation window because verification falls back to the previous algorithms).
"""
import hashlib
import os
from base64 import urlsafe_b64encode

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from config import config
from log import get_logger

log = get_logger(__name__)

_private_key = None
_public_pem = None
_kid = None


def _ensure_keypair():
    global _private_key, _public_pem, _kid
    if _private_key is not None:
        return
    path = config.get('jwt_key_path', 'certs/jwt-rsa.pem')
    try:
        with open(path, 'rb') as f:
            pem = f.read()
        _private_key = serialization.load_pem_private_key(pem, password=None)
        log.info('Loaded RSA signing key from %s', path)
    except FileNotFoundError:
        _private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048,
        )
        pem = _private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
        parent = os.path.dirname(os.path.abspath(path))
        os.makedirs(parent, exist_ok=True)
        tmp = f'{path}.tmp'
        with open(tmp, 'wb') as f:
            f.write(pem)
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
        log.warning(
            'Generated new RSA signing key at %s (RS256 tokens are signed with it)',
            path,
        )
    public_key = _private_key.public_key()
    _public_pem = public_key.public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode('utf-8')
    der = public_key.public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    # Stable per-key identifier derived from the public key (Google-style):
    # SHA-256 of the SPKI DER, truncated to 16 bytes, URL-safe base64.
    _kid = urlsafe_b64encode(hashlib.sha256(der).digest()[:16]).rstrip(b'=').decode()


def get_private_key():
    _ensure_keypair()
    return _private_key


def get_public_key_pem():
    _ensure_keypair()
    return _public_pem


def get_kid():
    _ensure_keypair()
    return _kid


def get_jwk():
    _ensure_keypair()
    numbers = _private_key.public_key().public_numbers()

    def _b64u_int(value):
        size = (value.bit_length() + 7) // 8
        return urlsafe_b64encode(value.to_bytes(size, 'big')).rstrip(b'=').decode()

    return {
        'kty': 'RSA',
        'use': 'sig',
        'alg': 'RS256',
        'kid': _kid,
        'n': _b64u_int(numbers.n),
        'e': _b64u_int(numbers.e),
    }