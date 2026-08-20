from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from app.core.db import Base


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    account_type = Column(String, nullable=False)  # e.g. "checking", "savings"
    balance_krw = Column(Integer, nullable=False, default=0)


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    occurred_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    merchant = Column(String, nullable=False)
    category = Column(String, nullable=False)  # e.g. "subscription", "dining", "transport"
    amount_krw = Column(Integer, nullable=False)
