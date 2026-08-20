from pydantic import BaseModel


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
