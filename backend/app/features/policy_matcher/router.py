from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.router import get_current_user
from app.core.db import get_db
from app.features.policy_matcher.categories import category_tags
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
        return RecommendationListResponse(
            recommendations=[RecommendationOut.model_validate(r) for r in rows],
            unread_count=unread_count,
        )
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        today = today_kst()
        counts: dict[str, int] = {}
        for row in db.query(CachedPolicy).all():
            status, _ = compute_policy_status(row.apply_start_ymd, row.apply_end_ymd, today)
            if status == "만료":
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
