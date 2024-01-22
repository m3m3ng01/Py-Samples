from flask_login import UserMixin
from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base,UserMixin):
    __tablename__ = "users"

    id = Column(Integer, autoincrement=True, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    address = Column(String(255), nullable=True)
    name = Column(String(100), nullable=False)
    phone_number= Column(String(30), nullable=True)
    is_active=Column(Boolean, nullable=False)

    def __repr__(self):
        return f"<User {self.email}>"

    def is_authenticated(self):
        return True  # Replace with your own logic

    def is_active(self):
        return self.is_active  # Replace with your own logic

    def get_id(self):
        return self.id