# ** App Modules
from app.helpers.logger import setup_log
from app.db import get_db


def register_logger():
    setup_log()


def db():
    return next(get_db())
