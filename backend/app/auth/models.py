from sqlalchemy import Boolean, Column, Integer, String

from app.core.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    age = Column(Integer, nullable=True)
    is_married = Column(Boolean, nullable=True)
    annual_income_krw = Column(Integer, nullable=True)
    region = Column(String, nullable=True)
