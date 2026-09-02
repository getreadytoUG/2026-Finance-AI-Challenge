from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.router import get_current_user
from app.core.db import get_db
from app.features.policy_matcher.models import CachedPolicy
from app.features.policy_matcher.schemas import PolicyMatchInput
from app.features.policy_matcher.status import today_kst
from app.features.savings_simulator.schemas import (
    HousingLoanInput,
    HousingLoanOutput,
    YouthLeapAccountInput,
    YouthLeapAccountOutput,
)
from app.features.savings_simulator.simulator import (
    match_real_housing_policies,
    match_real_savings_policies,
    simulate_housing_loan,
    simulate_youth_leap_account,
)

router = APIRouter()


def _match_input(current_user: User, annual_income_krw: int) -> PolicyMatchInput | None:
    # 실제 정책 매칭에는 나이·지역이 필수인데, 이 시뮬레이터 폼은 그 값들을 받지
    # 않는다 — 로그인한 유저의 저장된 프로필에서 채운다(입력폼엔 없는 정보를 다시
    # 물어보지 않기 위함). 온보딩을 마치지 않아 프로필이 비어있으면(이론상 이
    # 페이지까지 못 오지만 방어적으로) 실제 매칭은 건너뛴다.
    if current_user.age is None or current_user.region is None:
        return None
    return PolicyMatchInput(
        age=current_user.age,
        is_married=bool(current_user.is_married),
        annual_income_krw=annual_income_krw,
        region=current_user.region,
        spouse_annual_income_krw=current_user.spouse_annual_income_krw if current_user.is_married else None,
        has_disability=current_user.has_disability,
        is_veteran=current_user.is_veteran,
    )


@router.post("/youth_leap_account", response_model=YouthLeapAccountOutput)
def youth_leap_account(
    payload: YouthLeapAccountInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = simulate_youth_leap_account(payload)
    match_input = _match_input(current_user, payload.annual_income_krw)
    if match_input is not None:
        policies = db.query(CachedPolicy).all()
        result.matched_policies = match_real_savings_policies(policies, match_input, today_kst())
    return result


@router.post("/housing_loan", response_model=HousingLoanOutput)
def housing_loan(
    payload: HousingLoanInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = simulate_housing_loan(payload)
    # household_annual_income_krw는 이미 가구 합산 값이라 배우자 소득을 또 더하지
    # 않는다(_match_input의 spouse_annual_income_krw 처리와 다른 지점).
    match_input = _match_input(current_user, payload.household_annual_income_krw)
    if match_input is not None:
        match_input = match_input.model_copy(update={"spouse_annual_income_krw": None})
        policies = db.query(CachedPolicy).all()
        result.matched_policies = match_real_housing_policies(policies, payload.housing_type, match_input, today_kst())
    return result
