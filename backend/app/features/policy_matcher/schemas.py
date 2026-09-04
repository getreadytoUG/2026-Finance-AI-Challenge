from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

# app.auth.schemas.OccupationType과 값이 반드시 같아야 한다 — 여기서 재수입하지
# 않고 복제해둔 이유는 순환 임포트 때문이다: app.auth.service가
# policy_matcher.models를 임포트하고, features/__init__.py가 그걸 통해
# policy_chat.tool → policy_chat.schemas → policy_matcher.matching →
# policy_matcher.schemas로 이어지는데, 이 시점에 policy_matcher.schemas가
# app.auth.schemas를 다시 임포트하면 app.auth.schemas가 필요로 하는
# app.auth.service가 아직 로딩 중이라 ImportError가 난다(2026-09-03 실제로
# 재현됨). OccupationType이 바뀌면 auth/schemas.py도 같이 고칠 것.
OccupationType = Literal["student", "employee", "self_employed", "unemployed", "other"]


class PolicyMatchInput(BaseModel):
    age: int
    is_married: bool
    annual_income_krw: int
    region: str
    # 소득 조건은 가구소득 기준인 정책이 많아, 배우자 소득이 있으면 합산해서
    # 심사한다(matching.is_eligible 참고).
    spouse_annual_income_krw: int | None = None
    # 2026-09-02 추가: 장애인/국가보훈대상자 전용 정책 필터링(matching.is_eligible
    # 참고). None(미입력)이면 필터링하지 않는다(fail-open, 하위 호환).
    has_disability: bool | None = None
    is_veteran: bool | None = None
    # 2026-09-03 추가: "학생 아닌데 국가근로장학금이 뜬다"(사용자 지적) — 대학
    # 재학생 전용 정책이 나이/소득 조건만으로는 안 걸러진다(schoolCd라는 별도
    # 구조화 필드가 있는데 그동안 안 썼다). None(미입력)이면 필터링하지 않는다
    # (fail-open, matching.is_eligible 참고).
    occupation: OccupationType | None = None
    # 2026-09-03 추가: "중소기업 다니는데도 관련 없는 정책이 뜬다"(사용자 지적) —
    # sbizCd(정책특화요건코드)의 중소기업 전용(0014001) 정책을 거르는 데 쓴다.
    # User 모델에 이미 있던 필드(2026-09-01 UPGRADE.md 확장 프로필)를 재사용한다.
    is_sme_employee: bool | None = None


class PolicyOption(BaseModel):
    # "내 맞춤 정책 보기" 탭에서 정책별 챗봇(policy_qa)을 열려면 policy_key가 필요해서
    # 추가했다(2026-09-01) — 정책별 챗봇은 policy_key로 CachedPolicy를 조회한다.
    policy_key: str
    policy_name: str
    benefit_description: str
    application_period: str
    reference_url: str
    is_newlywed_policy: bool = False
    # 2026-09-02 QA에서 발견: 대시보드/"내 맞춤 정책 보기"가 이 필드 없이
    # "신청 가능"을 하드코딩해서 이미 마감된 정책에도 그대로 붙어 있었다
    # (정책 달력/AI 검색 쪽은 PolicyBrowseItem에 이미 있던 필드라 문제 없었음).
    # compute_policy_status()로 계산해서 채운다(tool.py 참고) — 기본값은
    # 필드 추가 이전 프론트/테스트가 값을 안 줘도 깨지지 않도록.
    status: str = "상시"
    status_emoji: str = "🟢"


class PolicyMatchOutput(BaseModel):
    options: list[PolicyOption]


class RecommendationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    # 2026-09-02 QA에서 발견: reference_url이 없는("링크 정보 없음") 추천 항목은
    # 클릭해도 아무 반응이 없었다 — 정책별 챗봇(PolicyChatDrawer)을 열려면
    # policy_key가 있어야 해서 추가한다.
    policy_key: str
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
    # 2026-09-03 추가("혼인신고 계산기 타겟팅" 재작업): 버팀목/디딤돌 실제 대출조건
    # 비교(marriage_comparison.compare_housing_loan_scenarios)에 필요한 입력 —
    # LTV·대출한도 계산은 목표가/자기자본이 있어야 의미 있는 금액이 나온다.
    # savings_simulator/HousingLoanInput과 동일한 기본값(2.5억/5천만원)을 쓴다.
    target_price_krw: int = 250_000_000
    self_capital_krw: int = 50_000_000


class MarriagePolicyItem(BaseModel):
    policy_key: str
    policy_name: str
    benefit_description: str
    application_period: str
    reference_url: str
    is_newlywed_policy: bool = False
    # 2026-09-03 추가: married_only/unmarried_only 버킷에 왜 그 정책이 속했는지
    # (혼인상태 조건 자체 때문인지, 가구소득 합산 때문인지) 설명하는 한 줄 —
    # marriage_comparison._change_reason 참고. both 버킷은 변화가 없으므로 None.
    change_reason: str | None = None


class HousingLoanScenario(BaseModel):
    eligible: bool
    product_name: str
    policy_rate: float
    ltv_rate: float
    loan_amount_krw: int
    monthly_interest_krw: int
    summary: str


class HousingLoanMarriageComparison(BaseModel):
    housing_type: Literal["jeonse", "purchase"]
    unmarried: HousingLoanScenario
    married: HousingLoanScenario


class MarriageComparisonOutput(BaseModel):
    # 2026-09-03 재작업("혼인신고 계산기도 특정 정책 타겟팅해야 함", 사용자 요청):
    # CachedPolicy 전체를 스캔해 자격 변화를 찾는 방식은 실제로 혼인상태를 조건으로
    # 거는 정책이 2,750건 중 71건뿐이라 대부분 밋밋한 결과만 냈다. 실제로 미혼용/
    # 기혼용 상품이 이름부터 따로 있고 조건도 다른 걸로 확인된 고정 기준 상품 2개
    # (버팀목/디딤돌 전세·구입자금대출)를 항상 우선 비교해서 보여준다
    # (marriage_comparison.compare_housing_loan_scenarios 참고).
    housing_loan_comparisons: list[HousingLoanMarriageComparison]
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
