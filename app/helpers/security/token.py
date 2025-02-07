from app.config import settings
import json
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from base64 import b64encode, b64decode
from cryptography.hazmat.backends import default_backend
from datetime import datetime, timedelta
from logzero import logger
import pytz 
from jose import JWTError, jwt


class Token:
    _secret_key = settings.AES_SECRET_KEY.encode('utf-8')
    if len(_secret_key) not in [16, 24, 32]:
        raise ValueError(f"Invalid key size ({len(_secret_key)}) for AES. Must be 16, 24, or 32 bytes")
    _block_size = 128

    @classmethod
    def encrypt_data(cls, data: dict) -> str:
        try:
            if not cls._secret_key:
                raise ValueError("Secret key not initialized")

            data_bytes = json.dumps(data).encode('utf-8')
            
            padder = padding.PKCS7(cls._block_size).padder()
            padded_data = padder.update(data_bytes) + padder.finalize()
            
            cipher = Cipher(algorithms.AES(cls._secret_key), modes.ECB(), backend=default_backend())
            encryptor = cipher.encryptor()
            encrypted_bytes = encryptor.update(padded_data) + encryptor.finalize()
            
            return b64encode(encrypted_bytes).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Encryption failed: {str(e)}")
            raise ValueError(f"Failed to encrypt data: {str(e)}")

    @classmethod
    def decrypt_data(cls, encrypted_data: str) -> dict:
        try:
            if not cls._secret_key:
                raise ValueError("Secret key not initialized")

            encrypted_bytes = b64decode(encrypted_data)
            
            cipher = Cipher(algorithms.AES(cls._secret_key), modes.ECB(), backend=default_backend())
            decryptor = cipher.decryptor()
            decrypted_padded = decryptor.update(encrypted_bytes) + decryptor.finalize()
            
            unpadder = padding.PKCS7(cls._block_size).unpadder()
            decrypted_bytes = unpadder.update(decrypted_padded) + unpadder.finalize()
            
            return json.loads(decrypted_bytes.decode('utf-8'))
            
        except Exception as e:
            logger.error(f"Decryption failed: {str(e)}")
            raise


    @staticmethod
    def create_jwt_token(data: dict, expires_delta: timedelta) -> str:
        """
        Create a JWT token with given data and expiration using UTC time
        """
        to_encode = data.copy()
        current_utc = datetime.now(pytz.UTC)
        expire_utc = current_utc + expires_delta
        
        to_encode.update({
            "exp": int(expire_utc.timestamp()),  # UTC timestamp for JWT
            "iat": int(current_utc.timestamp())  # UTC timestamp for JWT
        })
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.JWT_SECRET_KEY, 
            algorithm=settings.JWT_ALGORITHM
        )
        return encoded_jwt
    
    @staticmethod
    def verify_jwt_token(token: str) -> dict:
        """
        Verify a JWT token and return its payload
        """
        try:
            payload = jwt.decode(
                token, 
                settings.JWT_SECRET_KEY, 
                algorithms=[settings.JWT_ALGORITHM]
            )
            return payload
        except JWTError:
            return None