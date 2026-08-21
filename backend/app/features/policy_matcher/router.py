from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.router import get_current_user
from app.core.db import get_db
from app.features.policy_matcher.models import PolicyRecommendation
from app.features.policy_matcher.recommender import run_recommendation_batch_for_user
from app.features.policy_matcher.schemas import RecommendationListResponse, RecommendationOut, RefreshResponse

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
    return RecommendationListResponse(recommendations=[RecommendationOut.model_validate(r) for r in rows])
