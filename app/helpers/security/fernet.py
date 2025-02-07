# core/security.py
from cryptography.fernet import Fernet
from app.config import settings
import json

def encrypt_config(config: dict) -> str:
    """Encrypt sensitive database configuration"""
    f = Fernet(settings.FERNET_ENCRYPTION_KEY)
    return f.encrypt(json.dumps(config).encode()).decode()

def decrypt_config(encrypted_config: str) -> dict:
    """Decrypt database configuration"""
    f = Fernet(settings.FERNET_ENCRYPTION_KEY)
    return json.loads(f.decrypt(encrypted_config.encode()).decode())