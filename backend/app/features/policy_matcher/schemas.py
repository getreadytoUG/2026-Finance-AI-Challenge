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

    id: int
    policy_name: str
    benefit_description: str
    application_period: str
    reference_url: str
    matched_at: datetime
    is_read: bool


class RecommendationListResponse(BaseModel):
    recommendations: list[RecommendationOut]
    unread_count: int


class RefreshResponse(BaseModel):
    created: int


class PolicyBrowseItem(BaseModel):
    policy_name: str
    benefit_description: str
    application_period: str
    reference_url: str
    large_category: str
    status: str
    status_emoji: str


class PolicyBrowseResponse(BaseModel):
    items: list[PolicyBrowseItem]
    total: int
    page: int
    page_size: int


class PolicyCategoryItem(BaseModel):
    name: str
    count: int


class PolicyCategoryListResponse(BaseModel):
    categories: list[PolicyCategoryItem]
