from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SavingsPlanInput(BaseModel):
    monthly_income_krw: int
    goal_amount_krw: int
    goal_months: int


class SavingsAllocation(BaseModel):
    category: str
    monthly_amount_krw: int


class SavingsPlanOutput(BaseModel):
    allocations: list[SavingsAllocation]
    monthly_required_krw: int
    # 사용자가 AI 정책 분석에서 "저축플랜에 반영"한 정책들의 월 혜택 합계 —
    # savings_planner/tool.py가 DB에서 직접 조회해 채운다(클라이언트 입력 아님).
    linked_monthly_benefit_krw: int
    feasibility_warning: str | None = None


class LinkedBenefitIn(BaseModel):
    policy_key: str
    policy_name: str
    estimated_monthly_benefit_krw: int


class LinkedBenefitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    policy_key: str
    policy_name: str
    estimated_monthly_benefit_krw: int
    linked_at: datetime


class LinkedBenefitListResponse(BaseModel):
    items: list[LinkedBenefitOut]
    total_monthly_benefit_krw: int
