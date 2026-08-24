from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.router import get_current_user
from app.core.db import get_db
from app.features.policy_matcher.models import CachedPolicy, PolicyRecommendation
from app.features.policy_matcher.recommender import run_recommendation_batch_for_user
from app.features.policy_matcher.schemas import (
    PolicyBrowseItem,
    PolicyBrowseResponse,
    PolicyCategoryItem,
    PolicyCategoryListResponse,
    RecommendationListResponse,
    RecommendationOut,
    RefreshResponse,
)
from app.features.policy_matcher.status import compute_policy_status, today_kst

router = APIRouter()


@router.post("/recommendations/refresh", response_model=RefreshResponse)
def refresh_my_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Raising this uncaught (like run_recommendation_batch_for_user normally
    # does) would hit Starlette's default 500 handling, which sits outside
    # CORSMiddleware — the browser blocks the response entirely ("Failed to
    # fetch") instead of showing any error. Converting to HTTPException keeps
    # it on the handled-exception path CORSMiddleware still processes, same
    # as /tools/policy_matcher's ToolExecutionError -> HTTPException(400).
    try:
        created = run_recommendation_batch_for_user(db, current_user)
    except Exception as e:
        print(f"[ERROR] /policy_matcher/recommendations/refresh failed for user_id={current_user.id}: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    return RefreshResponse(created=created)


@router.get("/recommendations", response_model=RecommendationListResponse)
def list_my_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(PolicyRecommendation)
        .filter(PolicyRecommendation.user_id == current_user.id)
        .order_by(PolicyRecommendation.matched_at.desc())
        .all()
    )
    unread_count = sum(1 for row in rows if not row.is_read)
    return RecommendationListResponse(
        recommendations=[RecommendationOut.model_validate(r) for r in rows],
        unread_count=unread_count,
    )


@router.patch("/recommendations/{recommendation_id}/read", response_model=RecommendationOut)
def mark_recommendation_read(
    recommendation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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


@router.get("/browse", response_model=PolicyBrowseResponse)
def browse_policies(
    page: int = 1,
    page_size: int = 20,
    category: str | None = None,
    include_closed: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    today = today_kst()
    query = db.query(CachedPolicy)
    if category:
        query = query.filter(CachedPolicy.large_category == category)

    matched = []
    for row in query.all():
        status, emoji = compute_policy_status(row.apply_start_ymd, row.apply_end_ymd, today)
        if status == "마감" and not include_closed:
            continue
        matched.append((row, status, emoji))

    total = len(matched)
    start = (page - 1) * page_size
    page_rows = matched[start : start + page_size]

    return PolicyBrowseResponse(
        items=[
            PolicyBrowseItem(
                policy_name=row.policy_name,
                benefit_description=row.description,
                application_period=row.application_period,
                reference_url=row.apply_url,
                large_category=row.large_category,
                status=status,
                status_emoji=emoji,
            )
            for row, status, emoji in page_rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/categories", response_model=PolicyCategoryListResponse)
def list_policy_categories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    today = today_kst()
    counts: dict[str, int] = {}
    for row in db.query(CachedPolicy).all():
        status, _ = compute_policy_status(row.apply_start_ymd, row.apply_end_ymd, today)
        if status == "마감":
            continue
        counts[row.large_category] = counts.get(row.large_category, 0) + 1

    categories = [
        PolicyCategoryItem(name=name, count=count)
        for name, count in sorted(counts.items(), key=lambda pair: -pair[1])
    ]
    return PolicyCategoryListResponse(categories=categories)
