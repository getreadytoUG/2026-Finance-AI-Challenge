from pydantic import BaseModel


class PolicyMatchInput(BaseModel):
    age: int
    is_married: bool
    annual_income_krw: int
    region: str


class PolicyOption(BaseModel):
    policy_name: str
    eligible: bool
    benefit_description: str
    application_period: str
    reference_url: str


class PolicyMatchOutput(BaseModel):
    options: list[PolicyOption]
