from fastapi import APIRouter, Depends
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
    created = run_recommendation_batch_for_user(db, current_user)
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
