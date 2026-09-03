from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.features.policy_matcher.models import CachedPolicy
from app.features.policy_matcher.youth_center_client import fetch_all_policies


def refresh_policy_cache(db: Session) -> int:
    policies = fetch_all_policies()
    now = datetime.now(timezone.utc)

    existing = {row.policy_key: row for row in db.query(CachedPolicy).all()}
    seen_keys: set[str] = set()
    upserted = 0

    for policy in policies:
        policy_key = policy.policy_id or policy.policy_name
        if not policy_key or policy_key in seen_keys:
            continue
        seen_keys.add(policy_key)

        row = existing.get(policy_key)
        if row is None:
            row = CachedPolicy(policy_key=policy_key)
            db.add(row)

        row.policy_name = policy.policy_name
        row.description = policy.description
        row.apply_url = policy.apply_url
        row.application_period = policy.application_period
        row.apply_start_ymd = policy.apply_start_ymd
        row.apply_end_ymd = policy.apply_end_ymd
        row.large_category = policy.large_category
        row.mid_category = policy.mid_category
        row.min_age = policy.min_age
        row.max_age = policy.max_age
        row.min_income_krw = policy.min_income_krw
        row.max_income_krw = policy.max_income_krw
        row.marital_status = policy.marital_status
        row.region_code = policy.region_code
        row.institution_group_code = policy.institution_group_code
        row.school_code = policy.school_code
        row.job_code = policy.job_code
        row.sbiz_code = policy.sbiz_code
        row.refreshed_at = now
        upserted += 1

    db.commit()
    return upserted


def seed_policy_cache_if_empty(db: Session) -> None:
    if db.query(CachedPolicy.id).first() is None:
        refresh_policy_cache(db)
