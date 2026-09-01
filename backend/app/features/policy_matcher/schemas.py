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
    # "내 맞춤 정책 보기" 탭에서 정책별 챗봇(policy_qa)을 열려면 policy_key가 필요해서
    # 추가했다(2026-09-01) — 정책별 챗봇은 policy_key로 CachedPolicy를 조회한다.
    policy_key: str
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
    # 추천 탭 캘린더가 AI 검색 결과를 날짜별로 배치할 수 있도록 원본 마감일도
    # 함께 내려준다(status/status_emoji는 이미 계산된 요약값이라 날짜 자체는 없었음).
    apply_start_ymd: str | None = None
    apply_end_ymd: str | None = None


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


class PolicyRankingInput(MarriageComparisonInput):
    policy_keys: list[str]
    # 프롬프트에 "이 목록이 어떤 버킷인지" 알려주기 위한 설명 텍스트(프론트가 고정된
    # 문구 중 하나를 보냄, 사용자 자유 입력 아님) — 예: "혼인신고 후에만 자격되는 정책".
    context_label: str


class RankedPolicyItem(BaseModel):
    policy_key: str
    reason: str


class PolicyRankingOutput(BaseModel):
    # 배열 순서 자체가 우선순위(첫 번째가 가장 우선)다 — 별도 rank 정수 필드를 두지 않는다.
    ranked: list[RankedPolicyItem]
