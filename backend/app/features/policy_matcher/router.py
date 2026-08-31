from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.router import get_current_user
from app.core.db import get_db
from app.features.policy_matcher.categories import category_tags
from app.features.policy_matcher.marriage_comparison import build_marriage_scenarios, compare_marriage_scenarios
from app.features.policy_matcher.matching import REGIONS, region_matches
from app.features.policy_matcher.models import CachedPolicy, PolicyRecommendation
from app.features.policy_matcher.ranking import rank_policies
from app.features.policy_matcher.recommender import run_recommendation_batch_for_user
from app.features.policy_matcher.schemas import (
    MarriageComparisonInput,
    MarriageComparisonOutput,
    PolicyBrowseItem,
    PolicyBrowseResponse,
    PolicyCategoryItem,
    PolicyCategoryListResponse,
    PolicyRankingInput,
    PolicyRankingOutput,
    RecommendationListResponse,
    RecommendationOut,
    RefreshResponse,
    RegionListResponse,
)
from app.features.policy_matcher.status import STATUS_ORDER, compute_policy_status, today_kst

router = APIRouter()


def _raise_as_http_500(endpoint: str, context: str, e: Exception) -> None:
    # Raising uncaught (like the DB layer normally does) would hit Starlette's
    # default 500 handling, which sits outside CORSMiddleware — the browser
    # blocks the response entirely ("Failed to fetch") instead of showing any
    # error. Converting to HTTPException keeps it on the handled-exception
    # path CORSMiddleware still processes.
    print(f"[ERROR] {endpoint} failed{context}: {type(e).__name__}: {e}")
    raise HTTPException(status_code=500, detail=str(e))


@router.get("/regions", response_model=RegionListResponse)
def list_regions(current_user: User = Depends(get_current_user)):
    return RegionListResponse(regions=REGIONS)


@router.post("/recommendations/refresh", response_model=RefreshResponse)
def refresh_my_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        created = run_recommendation_batch_for_user(db, current_user)
    except Exception as e:
        _raise_as_http_500("/policy_matcher/recommendations/refresh", f" for user_id={current_user.id}", e)
    return RefreshResponse(created=created)


@router.get("/recommendations", response_model=RecommendationListResponse)
def list_my_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        rows = (
            db.query(PolicyRecommendation)
            .filter(PolicyRecommendation.user_id == current_user.id)
            .order_by(PolicyRecommendation.matched_at.desc())
            .all()
        )
        unread_count = sum(1 for row in rows if not row.is_read)

        # 신청 마감일(D-Day)은 PolicyRecommendation 테이블엔 없고 CachedPolicy에만
        # 있다 — /browse와 동일하게 policy_key로 조인해서 읽는다. cache.py의
        # refresh_policy_cache는 upsert만 하고 delete하지 않으므로(cache.py 참고)
        # 한번 추천된 policy_key는 항상 조회 가능하다는 전제로 안전하다.
        policy_keys = {row.policy_key for row in rows}
        cached_by_key = (
            {p.policy_key: p for p in db.query(CachedPolicy).filter(CachedPolicy.policy_key.in_(policy_keys)).all()}
            if policy_keys
            else {}
        )
        today = today_kst()

        recommendations = []
        for row in rows:
            cached = cached_by_key.get(row.policy_key)
            if cached is not None:
                status, emoji = compute_policy_status(cached.apply_start_ymd, cached.apply_end_ymd, today)
                apply_start_ymd, apply_end_ymd = cached.apply_start_ymd, cached.apply_end_ymd
            else:
                # 이론상만 발생(위 주석 참고) — 마감일 미상으로 안전하게 폴백한다.
                status, emoji = "상시", "🟢"
                apply_start_ymd, apply_end_ymd = None, None
            recommendations.append(
                RecommendationOut(
                    id=row.id,
                    policy_name=row.policy_name,
                    benefit_description=row.benefit_description,
                    application_period=row.application_period,
                    reference_url=row.reference_url,
                    matched_at=row.matched_at,
                    is_read=row.is_read,
                    apply_start_ymd=apply_start_ymd,
                    apply_end_ymd=apply_end_ymd,
                    status=status,
                    status_emoji=emoji,
                )
            )

        return RecommendationListResponse(recommendations=recommendations, unread_count=unread_count)
    except Exception as e:
        _raise_as_http_500("/policy_matcher/recommendations", f" for user_id={current_user.id}", e)


@router.patch("/recommendations/{recommendation_id}/read", response_model=RecommendationOut)
def mark_recommendation_read(
    recommendation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        row = (
            db.query(PolicyRecommendation)
            .filter(
                PolicyRecommendation.id == recommendation_id,
                PolicyRecommendation.user_id == current_user.id,
            )
            .first()
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Recommendation not found")
        row.is_read = True
        db.commit()
        db.refresh(row)
        return RecommendationOut.model_validate(row)
    except HTTPException:
        raise
    except Exception as e:
        _raise_as_http_500(
            f"/policy_matcher/recommendations/{recommendation_id}/read", f" for user_id={current_user.id}", e
        )


@router.get("/browse", response_model=PolicyBrowseResponse)
def browse_policies(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    category: str | None = None,
    region: str | None = None,
    include_closed: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        today = today_kst()

        matched = []
        for row in db.query(CachedPolicy).all():
            tags = category_tags(row.large_category)
            if category and category not in tags:
                continue
            # region_code가 비어있는 정책은 전국 대상이라 지역 필터로 걸러내지 않는다
            # (policy_matcher의 is_eligible과 동일한 fail-open 규칙, matching.py 참고).
            if region and row.region_code and not region_matches(row.region_code, region):
                continue
            status, emoji = compute_policy_status(row.apply_start_ymd, row.apply_end_ymd, today)
            if status == "만료" and not include_closed:
                continue
            matched.append((row, tags, status, emoji))

        matched.sort(key=lambda entry: STATUS_ORDER[entry[2]])

        total = len(matched)
        start = (page - 1) * page_size
        page_rows = matched[start : start + page_size]

        return PolicyBrowseResponse(
            items=[
                PolicyBrowseItem(
                    policy_key=row.policy_key,
                    policy_name=row.policy_name,
                    benefit_description=row.description,
                    application_period=row.application_period,
                    reference_url=row.apply_url,
                    large_category=", ".join(tags) if tags else "기타",
                    status=status,
                    status_emoji=emoji,
                )
                for row, tags, status, emoji in page_rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )
    except Exception as e:
        _raise_as_http_500("/policy_matcher/browse", f" for user_id={current_user.id}", e)


@router.get("/categories", response_model=PolicyCategoryListResponse)
def list_policy_categories(
    region: str | None = None,
    include_closed: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        today = today_kst()
        counts: dict[str, int] = {}
        for row in db.query(CachedPolicy).all():
            if region and row.region_code and not region_matches(row.region_code, region):
                continue
            status, _ = compute_policy_status(row.apply_start_ymd, row.apply_end_ymd, today)
            if status == "만료" and not include_closed:
                continue
            for tag in category_tags(row.large_category):
                counts[tag] = counts.get(tag, 0) + 1

        categories = [
            PolicyCategoryItem(name=name, count=count)
            for name, count in sorted(counts.items(), key=lambda pair: -pair[1])
        ]
        return PolicyCategoryListResponse(categories=categories)
    except Exception as e:
        _raise_as_http_500("/policy_matcher/categories", f" for user_id={current_user.id}", e)


@router.post("/marriage_comparison", response_model=MarriageComparisonOutput)
def compare_marriage_scenarios_endpoint(
    payload: MarriageComparisonInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 저장된 프로필을 읽지 않는 1회성 계산기 — 프론트가 getMe()로 미리 채워주고
    # 사용자가 그 자리에서 값(특히 배우자 소득)을 바꿔볼 수 있게 한다.
    try:
        policies = db.query(CachedPolicy).all()
        unmarried_input, married_input = build_marriage_scenarios(payload)
        return compare_marriage_scenarios(policies, unmarried_input, married_input, today_kst())
    except Exception as e:
        _raise_as_http_500("/policy_matcher/marriage_comparison", f" for user_id={current_user.id}", e)


@router.post("/marriage_comparison/rank", response_model=PolicyRankingOutput)
def rank_marriage_comparison_policies(
    payload: PolicyRankingInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 카드마다 자동으로 순위를 매기면 LLM 호출이 계속 쌓이므로, 사용자가 버킷별
    # "AI로 우선순위 정렬" 버튼을 눌렀을 때만 온디맨드로 그 버킷 전체를 한 번에 호출한다
    # (policy_chat.analyze_ai_search_policy와 동일한 온디맨드 원칙).
    try:
        policies = db.query(CachedPolicy).filter(CachedPolicy.policy_key.in_(payload.policy_keys)).all()
        return rank_policies(payload, policies)
    except Exception as e:
        _raise_as_http_500("/policy_matcher/marriage_comparison/rank", f" for user_id={current_user.id}", e)
