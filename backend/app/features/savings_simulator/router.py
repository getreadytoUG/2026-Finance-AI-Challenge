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
    YouthFutureSavingsInput,
    YouthFutureSavingsOutput,
)
from app.features.savings_simulator.simulator import (
    match_real_housing_policies,
    match_real_savings_policies,
    simulate_housing_loan,
    simulate_youth_future_savings,
)

router = APIRouter()


def _match_input(
    current_user: User,
    annual_income_krw: int,
    *,
    is_married: bool,
    spouse_annual_income_krw: int | None,
) -> PolicyMatchInput | None:
    # 실제 정책 매칭에는 나이·지역이 필수인데, 이 시뮬레이터 폼은 그 값들을 받지
    # 않는다 — 로그인한 유저의 저장된 프로필에서 채운다(입력폼엔 없는 정보를 다시
    # 물어보지 않기 위함). 온보딩을 마치지 않아 프로필이 비어있으면(이론상 이
    # 페이지까지 못 오지만 방어적으로) 실제 매칭은 건너뛴다.
    # 2026-09-06: is_married/spouse_annual_income_krw는 호출부가 정한다 — 폼의
    # 미혼/기혼 토글이 있으면 그 값을, 없으면(기존 호출) 저장된 프로필 값을 쓴다.
    if current_user.age is None or current_user.region is None:
        return None
    return PolicyMatchInput(
        age=current_user.age,
        is_married=is_married,
        annual_income_krw=annual_income_krw,
        region=current_user.region,
        spouse_annual_income_krw=spouse_annual_income_krw,
        has_disability=current_user.has_disability,
        is_veteran=current_user.is_veteran,
    )


@router.post("/youth_future_savings", response_model=YouthFutureSavingsOutput)
def youth_future_savings(
    payload: YouthFutureSavingsInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 2026-09-03: 나이(만 19~34세)/중소기업 재직여부(우대형 매칭)는 이 폼에 없는
    # 고정 프로필 값이라, marriage_comparison.py와 동일한 패턴으로 저장된 프로필에서
    # 채운다(폼엔 없는 정보를 다시 물어보지 않는다).
    result = simulate_youth_future_savings(
        payload, age=current_user.age, is_sme_employee=current_user.is_sme_employee
    )
    # 폼에 미혼/기혼 토글이 있으면(payload.is_married) 그 값을 쓰고, 기혼이면
    # payload.annual_income_krw가 이미 부부 합산이라 배우자 소득을 또 더하지 않는다.
    # 토글이 없으면(기존 호출) 예전처럼 저장된 프로필로 폴백한다.
    if payload.is_married is not None:
        is_married = payload.is_married
        spouse_income = None
    else:
        is_married = bool(current_user.is_married)
        spouse_income = current_user.spouse_annual_income_krw if current_user.is_married else None
    match_input = _match_input(
        current_user, payload.annual_income_krw, is_married=is_married, spouse_annual_income_krw=spouse_income
    )
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
    # 2026-09-06: 신혼가구 여부(소득상한/LTV/한도/금리표가 갈린다)는 이제 폼의
    # 미혼/기혼 토글(payload.is_married)이 결정한다 — 없으면(폼 외 호출/기존 테스트)
    # 저장된 프로필로 폴백한다. 청년전용 버팀목의 나이 조건은 폼에 없는 값이라
    # 그대로 프로필에서 넘긴다.
    is_married = payload.is_married if payload.is_married is not None else bool(current_user.is_married)
    result = simulate_housing_loan(payload, is_married=is_married, age=current_user.age)
    # household_annual_income_krw는 이미 가구 합산 값이라(미혼=본인 / 기혼=부부합산)
    # 배우자 소득을 또 더하지 않는다 — spouse_annual_income_krw=None으로 넘긴다.
    match_input = _match_input(
        current_user, payload.household_annual_income_krw, is_married=is_married, spouse_annual_income_krw=None
    )
    if match_input is not None:
        policies = db.query(CachedPolicy).all()
        result.matched_policies = match_real_housing_policies(policies, payload.housing_type, match_input, today_kst())
    return result
