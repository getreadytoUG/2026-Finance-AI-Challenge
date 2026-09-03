from typing import Literal

from pydantic import BaseModel


# 2026-09-03: 청년도약계좌는 2025-12-31부로 신규가입이 종료됐다(조세특례제한법상
# 비과세 혜택 일몰) — 후속 상품인 "청년미래적금"(2026-06-22 출시, 서민금융진흥원)
# 기준으로 시뮬레이터를 다시 만들었다. simulator.py 상단 주석에 출처를 남겨뒀다.
class YouthFutureSavingsInput(BaseModel):
    monthly_amount_krw: int
    annual_income_krw: int
    seed_money_krw: int = 0
    # 만기가 3년으로 고정된 상품이라(청년도약계좌처럼 3/5년 선택지가 없다) 더는
    # 입력받지 않는다 — simulator.py가 36개월로 고정 계산한다.


class MatchedSavingsPolicy(BaseModel):
    policy_key: str
    policy_name: str
    benefit_description: str
    application_period: str
    reference_url: str


class YouthFutureSavingsOutput(BaseModel):
    eligible: bool
    matching_rate: float
    eligibility_note: str
    policy_total_krw: int
    market_total_krw: int
    benefit_diff_krw: int
    summary: str
    # 2026-09-02 추가: 위 계산은 청년미래적금 실제 제도 수치를 반영하지만, 이 목록은
    # 별개로 실제 DB(CachedPolicy)에서 지금 입력한 나이·소득·지역 기준으로 자격되는
    # 저축/자산형성 정책을 찾아 보여준다(simulator.py의 match_real_savings_policies
    # 참고) — "이 상품 계산" vs "그 외 실제로 신청 가능한 정책"을 구분해서 보여주는
    # 게 목적이라 하나로 합치지 않는다.
    matched_policies: list[MatchedSavingsPolicy] = []


class HousingLoanInput(BaseModel):
    housing_type: Literal["jeonse", "purchase"]
    target_price_krw: int
    self_capital_krw: int
    household_annual_income_krw: int
    # 2026-09-03: 디딤돌대출은 실제로 대출기간(10/15/20/30년)마다 금리가 다르다
    # (simulator.py의 _PURCHASE_*_RATE_TABLE 참고) — 정확한 계산을 하려면 필요해서
    # 추가했다. jeonse(버팀목)에는 이런 기간별 금리 구조가 없어 무시된다.
    loan_term_years: Literal[10, 15, 20, 30] = 30
    # marriage_years 필드는 프론트 폼에 없었고 계산에도 안 쓰이던 죽은 필드라
    # 제거했다(2026-09-03) — 신혼가구 여부는 router.py가 로그인한 유저의 저장된
    # is_married 프로필 값을 simulate_housing_loan()에 직접 넘겨준다.


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
