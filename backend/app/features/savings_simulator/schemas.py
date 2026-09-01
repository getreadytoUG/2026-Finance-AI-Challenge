from typing import Literal

from pydantic import BaseModel


class YouthLeapAccountInput(BaseModel):
    monthly_amount_krw: int
    goal_years: Literal[3, 5]
    annual_income_krw: int
    seed_money_krw: int = 0


class YouthLeapAccountOutput(BaseModel):
    eligible: bool
    matching_rate: float
    eligibility_note: str
    policy_total_krw: int
    market_total_krw: int
    benefit_diff_krw: int
    summary: str


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
