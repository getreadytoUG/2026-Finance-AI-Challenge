from datetime import datetime

from pydantic import BaseModel, ConfigDict


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


class RecommendationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    policy_name: str
    benefit_description: str
    application_period: str
    reference_url: str
    matched_at: datetime


class RecommendationListResponse(BaseModel):
    recommendations: list[RecommendationOut]


class RefreshResponse(BaseModel):
    created: int
