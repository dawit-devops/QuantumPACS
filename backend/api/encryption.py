import base64

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from config import config
from log import get_logger

log = get_logger(__name__)


def _derive_key() -> bytes:
    raw = config.get('oauth_secret_encryption_key') or config.get('secret', '')
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'qpacs-oauth-enc-v1',
        iterations=600000,
    )
    return base64.urlsafe_b64encode(kdf.derive(raw.encode()))


_fernet: Fernet | None = None


def _get_fernet() -> Fernet | None:
    global _fernet
    if _fernet is None:
        try:
            _fernet = Fernet(_derive_key())
        except Exception as e:
            log.warning('Failed to initialize encryption: %s', e)
    return _fernet


def encrypt_secret(plaintext: str) -> str:
    if not plaintext:
        return ''
    f = _get_fernet()
    if f is None:
        raise RuntimeError('Encryption unavailable — cannot store secret')
    try:
        return f.encrypt(plaintext.encode()).decode()
    except Exception as e:
        log.error('Encryption failed: %s', e)
        raise


def decrypt_secret(ciphertext: str) -> str:
    if not ciphertext:
        return ''
    f = _get_fernet()
    if f is None:
        raise RuntimeError('Encryption unavailable — cannot decrypt secret')
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except Exception as e:
        log.warning('Decryption failed (may be legacy plaintext): %s', e)
        return ciphertext
