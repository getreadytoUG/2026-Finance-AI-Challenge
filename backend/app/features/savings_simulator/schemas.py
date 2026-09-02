from typing import Literal

from pydantic import BaseModel


class YouthLeapAccountInput(BaseModel):
    monthly_amount_krw: int
    goal_years: Literal[3, 5]
    annual_income_krw: int
    seed_money_krw: int = 0


class MatchedSavingsPolicy(BaseModel):
    policy_key: str
    policy_name: str
    benefit_description: str
    application_period: str
    reference_url: str


class YouthLeapAccountOutput(BaseModel):
    eligible: bool
    matching_rate: float
    eligibility_note: str
    policy_total_krw: int
    market_total_krw: int
    benefit_diff_krw: int
    summary: str
    # 2026-09-02 추가: 위 계산은 여전히 "청년도약계좌"류 상품 구조를 본뜬 예시
    # 수치지만, 이 목록은 실제 DB(CachedPolicy)에서 지금 입력한 나이·소득·지역
    # 기준으로 진짜 자격되는 저축/자산형성 정책을 찾아 보여준다(simulator.py의
    # match_real_savings_policies 참고) — "예시 계산" vs "실제로 신청 가능한 정책"을
    # 분리해서 보여주는 게 목적이라 하나로 합치지 않는다.
    matched_policies: list[MatchedSavingsPolicy] = []


class HousingLoanInput(BaseModel):
    housing_type: Literal["jeonse", "purchase"]
    target_price_krw: int
    self_capital_krw: int
    household_annual_income_krw: int
    marriage_years: int | None = None


class HousingLoanOutput(BaseModel):
    eligible: bool
    product_name: str
    ltv_rate: float
    policy_rate: float
    market_rate: float
    loan_amount_krw: int
    monthly_interest_krw: int
    market_monthly_interest_krw: int
    monthly_saving_krw: int
    summary: str
    # 위 계산과 마찬가지로 예시 상품 하나 대신, 실제 DB에서 지금 조건으로 진짜
    # 자격되는 전세/구입자금 대출이자 지원류 정책을 찾아 보여준다(2026-09-02 추가).
    matched_policies: list[MatchedSavingsPolicy] = []
