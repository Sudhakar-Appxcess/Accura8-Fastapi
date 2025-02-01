from app.db import get_db
from sqlalchemy.orm.query import Query
from sqlalchemy.orm.session import Session
from sqlalchemy import desc
from app.helper.decorator import response


class ORM:
    def __init__(self, model):
        db = next(get_db())
        self.q: Query = db.query(model)
        self.s: Session = db    # DB Session

    @response
    def first(self):
        return self.q.first()

    @response
    def last(self):
        return self.q.order_by(desc('id')).first()

    @response
    def fetch(self, key, value):
        return self.q.filter_by(key == value).all()

    @response
    def fetch_one(self, key, value):
        return self.q.filter_by(key == value).first()
