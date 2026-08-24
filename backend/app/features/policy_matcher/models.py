from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint

from app.core.db import Base


class PolicyRecommendation(Base):
    __tablename__ = "policy_recommendations"
    __table_args__ = (UniqueConstraint("user_id", "policy_key", name="uq_policy_recommendation_user_policy"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    policy_key = Column(String, nullable=False)
    policy_name = Column(String, nullable=False)
    benefit_description = Column(String, nullable=False)
    application_period = Column(String, nullable=False)
    reference_url = Column(String, nullable=False)
    matched_at = Column(DateTime(timezone=True), nullable=False)


class CachedPolicy(Base):
    __tablename__ = "cached_policies"

    id = Column(Integer, primary_key=True, index=True)
    policy_key = Column(String, nullable=False, unique=True, index=True)
    policy_name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    apply_url = Column(String, nullable=False)
    application_period = Column(String, nullable=False)
    apply_start_ymd = Column(String, nullable=True)
    apply_end_ymd = Column(String, nullable=True)
    large_category = Column(String, nullable=False, index=True)
    mid_category = Column(String, nullable=False)
    min_age = Column(Integer, nullable=True)
    max_age = Column(Integer, nullable=True)
    min_income_krw = Column(Integer, nullable=True)
    max_income_krw = Column(Integer, nullable=True)
    marital_status = Column(String, nullable=False)
    region_code = Column(String, nullable=False)
    refreshed_at = Column(DateTime(timezone=True), nullable=False)
