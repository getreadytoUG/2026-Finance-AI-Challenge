import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.auth.models import User
from app.features.policy_matcher.matching import is_eligible
from app.features.policy_matcher.models import PolicyRecommendation
from app.features.policy_matcher.schemas import PolicyMatchInput
from app.features.policy_matcher.youth_center_client import fetch_policies

logger = logging.getLogger(__name__)


def _has_complete_profile(user: User) -> bool:
    return (
        user.age is not None
        and user.is_married is not None
        and user.annual_income_krw is not None
        and user.region is not None
    )


def run_recommendation_batch_for_user(db: Session, user: User) -> int:
    if not _has_complete_profile(user):
        return 0

    match_input = PolicyMatchInput(
        age=user.age,
        is_married=user.is_married,
        annual_income_krw=user.annual_income_krw,
        region=user.region,
    )
    policies = fetch_policies(query=user.region)

    existing_keys = {
        row.policy_key
        for row in db.query(PolicyRecommendation.policy_key).filter(PolicyRecommendation.user_id == user.id)
    }

    created = 0
    for policy in policies:
        if not is_eligible(policy, match_input):
            continue
        policy_key = policy.policy_id or policy.policy_name
        if policy_key in existing_keys:
            continue
        db.add(
            PolicyRecommendation(
                user_id=user.id,
                policy_key=policy_key,
                policy_name=policy.policy_name,
                benefit_description=policy.description,
                application_period=policy.application_period,
                reference_url=policy.apply_url,
                matched_at=datetime.now(timezone.utc),
            )
        )
        existing_keys.add(policy_key)
        created += 1

    db.commit()
    return created


def run_recommendation_batch_for_all_users(db: Session) -> int:
    total_created = 0
    users = db.query(User).all()
    for user in users:
        if not _has_complete_profile(user):
            continue
        try:
            total_created += run_recommendation_batch_for_user(db, user)
        except Exception:
            logger.exception("policy recommendation batch failed for user_id=%s", user.id)
            db.rollback()
    return total_created
