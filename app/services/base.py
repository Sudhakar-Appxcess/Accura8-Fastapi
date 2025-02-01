# ** App Modules
from app.helpers.orm import ORM


class BaseService:
    def __init__(self, model):
        self.o = ORM(model)
        self.s = self.o.s
        self.q = self.o.q