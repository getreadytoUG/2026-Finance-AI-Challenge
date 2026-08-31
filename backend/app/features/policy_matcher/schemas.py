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
    # CachedPolicy를 policy_key로 조인해서 채운다(PolicyRecommendation 테이블 자체엔
    # 없는 필드) — router.list_my_recommendations 참고. 매칭되는 CachedPolicy를 못
    # 찾으면(이론상만 발생, cache.py는 upsert만 하고 delete하지 않음) 상시/None으로
    # 안전하게 폴백한다.
    apply_start_ymd: str | None = None
    apply_end_ymd: str | None = None
    status: str = "상시"
    status_emoji: str = "🟢"


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


class MarriageComparisonInput(BaseModel):
    age: int
    region: str
    annual_income_krw: int
    spouse_age: int | None = None
    spouse_annual_income_krw: int | None = None


class MarriagePolicyItem(BaseModel):
    policy_key: str
    policy_name: str
    benefit_description: str
    application_period: str
    reference_url: str
    is_newlywed_policy: bool = False


class MarriageComparisonOutput(BaseModel):
    married_only: list[MarriagePolicyItem]
    unmarried_only: list[MarriagePolicyItem]
    both: list[MarriagePolicyItem]
