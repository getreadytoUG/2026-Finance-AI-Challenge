import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.router import require_admin
from app.core.db import get_db
from app.features.admin.schemas import (
    AdminCategoryStat,
    AdminOverview,
    AdminPolicyStatsResponse,
    AdminRefreshResponse,
    AdminStatusStat,
    AdminUserItem,
    AdminUserListResponse,
)
from app.features.policy_matcher.cache import refresh_policy_cache
from app.features.policy_matcher.categories import category_tags
from app.features.policy_matcher.matching import is_likely_template_region_code
from app.features.policy_matcher.models import CachedPolicy, PolicyRecommendation
from app.features.policy_matcher.status import STATUS_ORDER, compute_policy_status, today_kst

router = APIRouter()
logger = logging.getLogger(__name__)


def _raise_as_http_500(endpoint: str, e: Exception) -> None:
    logger.exception(f"[ERROR] {endpoint} failed: {type(e).__name__}: {e}")
    raise HTTPException(status_code=500, detail=str(e))


@router.get("/overview", response_model=AdminOverview)
def get_overview(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        users = db.query(User).all()
        policies = db.query(CachedPolicy).all()
        recommendations = db.query(PolicyRecommendation).all()
        today = today_kst()

        return AdminOverview(
            total_users=len(users),
            married_users=sum(1 for u in users if u.is_married),
            total_policies=len(policies),
            last_cache_refreshed_at=max((p.refreshed_at for p in policies), default=None),
            policies_missing_link=sum(1 for p in policies if not p.apply_url),
            policies_expired=sum(
                1
                for p in policies
                if compute_policy_status(p.apply_start_ymd, p.apply_end_ymd, today)[0] == "만료"
            ),
            nationwide_template_policies=sum(1 for p in policies if is_likely_template_region_code(p)),
            total_recommendations=len(recommendations),
            unread_recommendations=sum(1 for r in recommendations if not r.is_read),
        )
    except Exception as e:
        _raise_as_http_500("/admin/overview", e)


@router.get("/users", response_model=AdminUserListResponse)
def list_users(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        users = db.query(User).order_by(User.id).all()
        return AdminUserListResponse(
            users=[
                AdminUserItem(
                    id=u.id,
                    email=u.email,
                    age=u.age,
                    is_married=u.is_married,
                    annual_income_krw=u.annual_income_krw,
                    region=u.region,
                    occupation=u.occupation,
                )
                for u in users
            ],
            total=len(users),
        )
    except Exception as e:
        _raise_as_http_500("/admin/users", e)


@router.get("/policies/stats", response_model=AdminPolicyStatsResponse)
def get_policy_stats(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        today = today_kst()
        policies = db.query(CachedPolicy).all()

        category_counts: dict[str, int] = {}
        status_counts: dict[str, int] = dict.fromkeys(STATUS_ORDER, 0)
        missing_link = 0
        template_count = 0

        for p in policies:
            for tag in category_tags(p.large_category):
                category_counts[tag] = category_counts.get(tag, 0) + 1
            status, _ = compute_policy_status(p.apply_start_ymd, p.apply_end_ymd, today)
            status_counts[status] += 1
            if not p.apply_url:
                missing_link += 1
            if is_likely_template_region_code(p):
                template_count += 1

        return AdminPolicyStatsResponse(
            total=len(policies),
            by_category=[
                AdminCategoryStat(name=name, count=count)
                for name, count in sorted(category_counts.items(), key=lambda kv: -kv[1])
            ],
            by_status=[AdminStatusStat(status=s, count=status_counts[s]) for s in STATUS_ORDER],
            missing_link_count=missing_link,
            nationwide_template_count=template_count,
            last_refreshed_at=max((p.refreshed_at for p in policies), default=None),
        )
    except Exception as e:
        _raise_as_http_500("/admin/policies/stats", e)


@router.post("/policies/refresh", response_model=AdminRefreshResponse)
def trigger_policy_refresh(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    # 새벽 3시 배치를 기다리지 않고 관리자가 즉시 온통청년 API를 다시 당겨오고
    # 싶을 때 쓰는 수동 트리거 — recommender.py의 배치와 동일한 함수를 재사용한다.
    try:
        upserted = refresh_policy_cache(db)
        return AdminRefreshResponse(upserted=upserted)
    except Exception as e:
        _raise_as_http_500("/admin/policies/refresh", e)
