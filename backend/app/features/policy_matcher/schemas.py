from pydantic import BaseModel


class PolicyMatchInput(BaseModel):
    age: int
    is_married: bool
    annual_income_krw: int
    region: str


class PolicyOption(BaseModel):
    policy_name: str
    eligible: bool
    preferential_rate_percent: float
    reference_url: str


class PolicyMatchOutput(BaseModel):
    options: list[PolicyOption]
