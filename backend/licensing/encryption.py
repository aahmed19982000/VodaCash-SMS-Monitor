# backend/licensing/encryption.py
import base64
import hashlib
from django.conf import settings
from cryptography.fernet import Fernet
import logging

logger = logging.getLogger("VodaCash.Encryption")

# Generate a consistent key from Django's SECRET_KEY
try:
    _key = base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode()).digest())
    _cipher = Fernet(_key)
except Exception as e:
    logger.error(f"Failed to initialize Fernet encryption cipher: {e}")
    _cipher = None

def encrypt_val(val: str) -> str:
    """تشفير النص باستخدام مفتاح متماثل مشتق من SECRET_KEY"""
    if not val or _cipher is None:
        return val or ""
    try:
        return _cipher.encrypt(val.encode('utf-8')).decode('utf-8')
    except Exception as e:
        logger.error(f"Encryption error: {e}")
        return val

def decrypt_val(val: str) -> str:
    """فك تشفير النص تلقائياً، وفي حال الفشل يرجع النص الأصلي"""
    if not val or _cipher is None:
        return val or ""
    try:
        if val.startswith("gAAAA"):
            return _cipher.decrypt(val.encode('utf-8')).decode('utf-8')
    except Exception as e:
        logger.debug(f"Decryption failed: {e}")
    return val
