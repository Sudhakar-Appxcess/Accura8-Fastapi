# helpers/password.py
import bcrypt
from logzero import logger

def hash_password(password: str) -> str:
    logger.debug("Hashing password")
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()