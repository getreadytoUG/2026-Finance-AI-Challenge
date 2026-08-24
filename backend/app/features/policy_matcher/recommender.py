import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from app.auth.models import User
from app.core.db import SessionLocal
from app.features.policy_matcher.cache import refresh_policy_cache
from app.features.policy_matcher.matching import is_eligible
from app.features.policy_matcher.models import PolicyRecommendation
from app.features.policy_matcher.schemas import PolicyMatchInput
from app.features.policy_matcher.youth_center_client import fetch_all_policies

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
    # fetch_policies()의 기본 page_size(100)로는 전체 카탈로그(~2,700여 건) 중
    # 일부만 보게 되어 상당수 매칭을 놓친다 — 전체를 가져온다.
    policies = fetch_all_policies()

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
            logger.exception("[ERROR] policy recommendation batch failed for user_id=%s", user.id)
            db.rollback()
    return total_created


scheduler = BackgroundScheduler(timezone="Asia/Seoul")


def _run_daily_recommendation_job() -> None:
    db = SessionLocal()
    try:
        refresh_policy_cache(db)
        run_recommendation_batch_for_all_users(db)
    finally:
        db.close()


def register_daily_recommendation_job() -> None:
    scheduler.add_job(
        _run_daily_recommendation_job,
        "cron",
        hour=3,
        id="daily_policy_recommendation",
        replace_existing=True,
    )
