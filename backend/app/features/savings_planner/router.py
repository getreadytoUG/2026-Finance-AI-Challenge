import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.router import get_current_user
from app.core.db import get_db
from app.features.savings_planner.models import SavingsLinkedBenefit
from app.features.savings_planner.schemas import LinkedBenefitIn, LinkedBenefitListResponse, LinkedBenefitOut

router = APIRouter()
logger = logging.getLogger(__name__)


def _raise_as_http_500(endpoint: str, context: str, e: Exception) -> None:
    logger.exception(f"[ERROR] {endpoint} failed{context}: {type(e).__name__}: {e}")
    raise HTTPException(status_code=500, detail=str(e))


@router.get("/linked_benefits", response_model=LinkedBenefitListResponse)
def list_linked_benefits(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        rows = (
            db.query(SavingsLinkedBenefit)
            .filter(SavingsLinkedBenefit.user_id == current_user.id)
            .order_by(SavingsLinkedBenefit.linked_at.desc())
            .all()
        )
        return LinkedBenefitListResponse(
            items=[LinkedBenefitOut.model_validate(r) for r in rows],
            total_monthly_benefit_krw=sum(r.estimated_monthly_benefit_krw for r in rows),
        )
    except Exception as e:
        _raise_as_http_500("/savings_planner/linked_benefits", f" for user_id={current_user.id}", e)


@router.post("/linked_benefits", response_model=LinkedBenefitOut, status_code=201)
def link_benefit(
    payload: LinkedBenefitIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 같은 정책을 다시 분석하고 다시 누르면 새 행을 만들지 않고 금액/시각만
    # 갱신한다 — UniqueConstraint(user_id, policy_key) 위반을 피하면서도
    # 재클릭이 자연스럽게 동작하게 한다.
    try:
        row = (
            db.query(SavingsLinkedBenefit)
            .filter(
                SavingsLinkedBenefit.user_id == current_user.id,
                SavingsLinkedBenefit.policy_key == payload.policy_key,
            )
            .first()
        )
        if row is None:
            row = SavingsLinkedBenefit(user_id=current_user.id, policy_key=payload.policy_key)
            db.add(row)
        row.policy_name = payload.policy_name
        row.estimated_monthly_benefit_krw = payload.estimated_monthly_benefit_krw
        row.linked_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(row)
        return LinkedBenefitOut.model_validate(row)
    except Exception as e:
        _raise_as_http_500("/savings_planner/linked_benefits", f" for user_id={current_user.id}", e)


@router.delete("/linked_benefits/{benefit_id}", status_code=204)
def unlink_benefit(
    benefit_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        row = (
            db.query(SavingsLinkedBenefit)
            .filter(SavingsLinkedBenefit.id == benefit_id, SavingsLinkedBenefit.user_id == current_user.id)
            .first()
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Linked benefit not found")
        db.delete(row)
        db.commit()
    except HTTPException:
        raise
    except Exception as e:
        _raise_as_http_500(
            f"/savings_planner/linked_benefits/{benefit_id}", f" for user_id={current_user.id}", e
        )
