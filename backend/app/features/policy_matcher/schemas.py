from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PolicyMatchInput(BaseModel):
    age: int
    is_married: bool
    annual_income_krw: int
    region: str
    # 소득 조건은 가구소득 기준인 정책이 많아, 배우자 소득이 있으면 합산해서
    # 심사한다(matching.is_eligible 참고).
    spouse_annual_income_krw: int | None = None


class PolicyOption(BaseModel):
    policy_name: str
    benefit_description: str
    application_period: str
    reference_url: str
    is_newlywed_policy: bool = False


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
    policy_key: str
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


class RegionListResponse(BaseModel):
    regions: list[str]
