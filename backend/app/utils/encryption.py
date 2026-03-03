"""API 키 AES-256-GCM 암호화"""
import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app.config import settings


def _get_encryption_key() -> bytes:
    key_hex = settings.ENCRYPTION_KEY
    key_bytes = bytes.fromhex(key_hex)
    if len(key_bytes) != 32:
        raise ValueError(
            "ENCRYPTION_KEY must be 64 hex chars. Generate: openssl rand -hex 32"
        )
    return key_bytes


def encrypt_api_key(plain_text: str) -> str:
    key = _get_encryption_key()
    aesgcm = AESGCM(key)
    iv = os.urandom(12)
    ciphertext = aesgcm.encrypt(iv, plain_text.encode("utf-8"), None)
    return base64.b64encode(iv + ciphertext).decode("utf-8")


def decrypt_api_key(encrypted_text: str) -> str:
    try:
        key = _get_encryption_key()
        aesgcm = AESGCM(key)
        encrypted_data = base64.b64decode(encrypted_text)
        iv = encrypted_data[:12]
        ciphertext = encrypted_data[12:]
        return aesgcm.decrypt(iv, ciphertext, None).decode("utf-8")
    except Exception as e:
        raise ValueError(f"API 키 복호화 실패: {str(e)}")
