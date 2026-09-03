import logging
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import get_args

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.router import require_admin
from app.core.db import get_db
from app.features.admin.schemas import (
    AdminCategoryStat,
    AdminCategoryTag,
    AdminCodeValuesResponse,
    AdminMaritalStatusCode,
    AdminMidCategoryValue,
    AdminOverview,
    AdminPolicyItem,
    AdminPolicyListResponse,
    AdminPolicyStatsResponse,
    AdminRefreshResponse,
    AdminRegionPrefix,
    AdminSignupTrendPoint,
    AdminSignupTrendResponse,
    AdminStatusStat,
    AdminUserItem,
    AdminUserListResponse,
)
from app.features.policy_matcher.cache import refresh_policy_cache
from app.features.policy_matcher.categories import PolicyCategoryTag, category_tags
from app.features.policy_matcher.matching import (
    MARITAL_STATUS_LABELS,
    is_likely_template_region_code,
    region_names_for_prefix,
)
from app.features.policy_matcher.models import CachedPolicy, PolicyRecommendation
from app.features.policy_matcher.status import STATUS_ORDER, compute_policy_status, today_kst

router = APIRouter()
logger = logging.getLogger(__name__)

# status.py에 동일한 상수가 있지만 그쪽은 모듈 비공개(_KST)라 여기서 다시 정의한다 —
# 가입 시각(UTC로 저장됨)을 관리자 화면 기준 날짜(KST)로 묶어 집계하는 데 쓴다.
_KST = timezone(timedelta(hours=9))


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
                    created_at=u.created_at,
                )
                for u in users
            ],
            total=len(users),
        )
    except Exception as e:
        _raise_as_http_500("/admin/users", e)


@router.get("/users/signup-trend", response_model=AdminSignupTrendResponse)
def get_signup_trend(
    days: int = 14,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    # created_at은 이 컬럼을 추가하기 전에 가입한 유저에겐 없다(User.created_at
    # 주석 참고) — 그런 유저는 추이 집계에서 빼고 별도로 개수만 알려준다.
    try:
        users = db.query(User).all()
        today = today_kst()
        counts: dict[str, int] = {}
        d = today - timedelta(days=days - 1)
        while d <= today:
            counts[d.isoformat()] = 0
            d += timedelta(days=1)

        unknown = 0
        for u in users:
            if u.created_at is None:
                unknown += 1
                continue
            key = u.created_at.astimezone(_KST).date().isoformat()
            if key in counts:
                counts[key] += 1

        return AdminSignupTrendResponse(
            points=[AdminSignupTrendPoint(date=date, count=count) for date, count in counts.items()],
            unknown_signup_date_count=unknown,
        )
    except Exception as e:
        _raise_as_http_500("/admin/users/signup-trend", e)


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


@router.get("/policies/list", response_model=AdminPolicyListResponse)
def list_policies(
    keyword: str | None = None,
    category: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        today = today_kst()
        matched: list[tuple[CachedPolicy, list[str], str]] = []
        for p in db.query(CachedPolicy).all():
            if keyword and keyword not in p.policy_name:
                continue
            tags = category_tags(p.large_category)
            if category and category not in tags:
                continue
            status_value, _ = compute_policy_status(p.apply_start_ymd, p.apply_end_ymd, today)
            if status and status_value != status:
                continue
            matched.append((p, tags, status_value))

        matched.sort(key=lambda entry: STATUS_ORDER[entry[2]])

        total = len(matched)
        start = (page - 1) * page_size
        page_rows = matched[start : start + page_size]

        return AdminPolicyListResponse(
            items=[
                AdminPolicyItem(
                    policy_key=p.policy_key,
                    policy_name=p.policy_name,
                    description=p.description,
                    large_category=", ".join(tags) or "기타",
                    status=status_value,
                    application_period=p.application_period,
                    region_code=p.region_code or "전국",
                    apply_url=p.apply_url,
                    refreshed_at=p.refreshed_at,
                )
                for p, tags, status_value in page_rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )
    except Exception as e:
        _raise_as_http_500("/admin/policies/list", e)


@router.get("/policies/code-values", response_model=AdminCodeValuesResponse)
def get_code_values(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    # 별도 테이블을 안 두고 매 요청마다 cached_policies를 그대로 집계한다 — 배치가
    # 갱신할 때마다(또는 "지금 갱신" 수동 트리거 시) 자동으로 최신 상태가 되므로
    # 이 화면 자체를 위한 갱신 로직이 따로 필요 없다(admin/schemas.py 주석 참고).
    try:
        policies = db.query(CachedPolicy).all()

        marital_counts = Counter(p.marital_status for p in policies)
        marital_status_codes = [
            AdminMaritalStatusCode(value=value, count=count, label=MARITAL_STATUS_LABELS.get(value))
            for value, count in sorted(marital_counts.items(), key=lambda kv: -kv[1])
        ]

        nationwide_region_count = sum(1 for p in policies if not p.region_code)
        prefix_counts: Counter[str] = Counter()
        for p in policies:
            if not p.region_code:
                continue
            # 같은 정책 안에 같은 접두사가 여러 번 나와도(예: "11110,11140") 정책
            # 1건으로만 센다 — set으로 중복 제거 후 접두사별로 1씩 더한다.
            prefixes = {code.strip()[:2] for code in p.region_code.split(",") if code.strip()}
            for prefix in prefixes:
                prefix_counts[prefix] += 1
        region_prefixes = [
            AdminRegionPrefix(prefix=prefix, count=count, mapped_region_names=region_names_for_prefix(prefix))
            for prefix, count in sorted(prefix_counts.items(), key=lambda kv: -kv[1])
        ]

        known_tags = set(get_args(PolicyCategoryTag))
        tag_counts: Counter[str] = Counter()
        for p in policies:
            for tag in category_tags(p.large_category):
                tag_counts[tag] += 1
        large_category_tags = [
            AdminCategoryTag(value=value, count=count, is_known=value in known_tags)
            for value, count in sorted(tag_counts.items(), key=lambda kv: -kv[1])
        ]

        mid_counts = Counter(p.mid_category for p in policies if p.mid_category)
        mid_categories = [
            AdminMidCategoryValue(value=value, count=count)
            for value, count in sorted(mid_counts.items(), key=lambda kv: -kv[1])
        ]

        return AdminCodeValuesResponse(
            generated_at=datetime.now(timezone.utc),
            cache_last_refreshed_at=max((p.refreshed_at for p in policies), default=None),
            total_policies=len(policies),
            marital_status_codes=marital_status_codes,
            nationwide_region_count=nationwide_region_count,
            region_prefixes=region_prefixes,
            large_category_tags=large_category_tags,
            mid_categories=mid_categories,
        )
    except Exception as e:
        _raise_as_http_500("/admin/policies/code-values", e)


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
