from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint

from app.core.db import Base


class SavingsLinkedBenefit(Base):
    __tablename__ = "savings_linked_benefits"
    __table_args__ = (UniqueConstraint("user_id", "policy_key", name="uq_savings_linked_benefit_user_policy"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    policy_key = Column(String, nullable=False)
    policy_name = Column(String, nullable=False)
    estimated_monthly_benefit_krw = Column(Integer, nullable=False)
    linked_at = Column(DateTime(timezone=True), nullable=False)
