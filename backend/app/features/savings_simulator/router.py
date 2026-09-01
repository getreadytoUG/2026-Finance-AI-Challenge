from fastapi import APIRouter, Depends

from app.auth.models import User
from app.auth.router import get_current_user
from app.features.savings_simulator.schemas import (
    HousingLoanInput,
    HousingLoanOutput,
    YouthLeapAccountInput,
    YouthLeapAccountOutput,
)
from app.features.savings_simulator.simulator import simulate_housing_loan, simulate_youth_leap_account

router = APIRouter()


@router.post("/youth_leap_account", response_model=YouthLeapAccountOutput)
def youth_leap_account(
    payload: YouthLeapAccountInput,
    current_user: User = Depends(get_current_user),
):
    # 결정적 계산이라 DB 조회/저장이 필요 없다 — 인증만 걸어 로그인 유저만 쓰게 한다.
    return simulate_youth_leap_account(payload)


@router.post("/housing_loan", response_model=HousingLoanOutput)
def housing_loan(
    payload: HousingLoanInput,
    current_user: User = Depends(get_current_user),
):
    return simulate_housing_loan(payload)
