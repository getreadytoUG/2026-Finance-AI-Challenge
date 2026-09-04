from typing import Literal

from pydantic import BaseModel

from app.features.policy_matcher.categories import PolicyCategoryTag
from app.features.policy_matcher.matching import PolicyRegion
from app.features.policy_matcher.schemas import OccupationType, PolicyBrowseItem
from app.features.policy_matcher.status import PolicyStatusLabel


class PolicyChatSearchInput(BaseModel):
    # 자연어 질의는 조건을 다 언급하지 않는 경우가 많다 — 언급 안 된 필드는
    # router에서 사용자 프로필 기본값으로 채운 뒤 이 스키마로 넘어온다.
    # region/category/status는 일부러 자유 텍스트가 아니라 Literal로 제한한다 —
    # 자유 텍스트로 두면 모델이 "마감 임박"처럼 실제 데이터와 안 맞는 표현을 만들어
    # keyword/region 매칭이 조용히 실패하는 문제가 있었다(2026-08-26 실사용 중 발견).
    age: int | None = None
    is_married: bool | None = None
    annual_income_krw: int | None = None
    spouse_annual_income_krw: int | None = None
    region: PolicyRegion | None = None
    keyword: str | None = None
    # "AI로 정책 알기" 탭 전용 필드. 기존 위젯 챗봇(policy_chat_search)은 시스템
    # 프롬프트에서 이 필드를 모델에게 알려주지 않으므로 항상 None으로 남아
    # 동작에 영향이 없다 — ai_search.py에서만 실제로 채워진다.
    category: PolicyCategoryTag | None = None
    status: PolicyStatusLabel | None = None
    # 2026-09-02 추가, 2026-09-05 3단계로 확장(사용자 요청: "전체/해당 없음/해당
    # 있음으로 다 걸게 해줘") — "장애인 대상"/"보훈대상자 대상" 좁혀보기 필터. 다른
    # 필드들(age/is_married/...)과 달리 사용자 자신의 프로필 값(has_disability/
    # is_veteran)으로 자동 채우지 않는다(router._profile_default_filters 참고) —
    # "나에게 맞는 정책만"이 아니라 "이 대상군을 어떻게 보고 싶은지" 명시적 열람
    # 선택이다. None(기본값)은 전체(필터링 안 함), "only"는 그 대상군 전용 정책만,
    # "exclude"는 그 대상군 전용 정책을 뺀 나머지만(policy_matcher.is_eligible이
    # 비장애인/비보훈대상자에게 자동으로 적용하는 것과 같은 결과를 여기서도 명시적
    # 으로 고를 수 있게 한다) 보여준다(tool.py._matches 참고).
    disability_filter: Literal["exclude", "only"] | None = None
    veteran_filter: Literal["exclude", "only"] | None = None
    # 2026-09-04 추가(사용자 지적: "정책달력 맞춤검색결과랑 한눈에보기 신청가능
    # 정책 개수가 왜 달라?") — policy_matcher.is_eligible()의 TARGETING_RULES는
    # 재학생/재직자/자영업자/미취업자/중소기업재직 "전용" 정책을 프로필이 안 맞으면
    # 자동 제외하는데, 이 스키마엔 애초에 occupation/is_sme_employee 필드가 없어서
    # ai_search._matches()가 그 필터를 아예 못 걸었다 — "맞춤"이라는 이름과 달리
    # 직업 조건과 무관한 전용 정책까지 다 섞여 나와 개수가 더 크게 나온 원인이었다.
    occupation: OccupationType | None = None
    is_sme_employee: bool | None = None


FilterFieldName = Literal[
    "age",
    "is_married",
    "annual_income_krw",
    "spouse_annual_income_krw",
    "region",
    "keyword",
    "category",
    "status",
    "disability_filter",
    "veteran_filter",
    "occupation",
    "is_sme_employee",
]


class PolicyAiFilterDelta(PolicyChatSearchInput):
    # 언급 안 된 필드는 "생략"(JSON에 키 자체가 없음)으로 표현해 이전 값을 유지하는
    # 방식이라, "이 필드를 명시적으로 지워라"는 의도를 표현할 방법이 따로 없었다
    # (2026-08-27 실사용 중 발견 — 이전 keyword가 계속 AND로 남아 새 검색이 계속
    # 0건으로 나오는데도 사용자가 채팅으로 지울 방법이 없었다). 값 필드와 별도로
    # 두어, "새 값으로 바꾼다"와 "그냥 지운다"를 구분할 수 있게 한다.
    clear_fields: list[FilterFieldName] | None = None


class PolicyChatSearchOption(BaseModel):
    policy_name: str
    benefit_description: str
    application_period: str
    reference_url: str
    is_newlywed_policy: bool
    status: str
    status_emoji: str


class PolicyChatSearchOutput(BaseModel):
    options: list[PolicyChatSearchOption]


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


class ChatResponse(BaseModel):
    reply: str
    policies: list[PolicyChatSearchOption] = []


class AiSearchMessageRequest(BaseModel):
    messages: list[ChatMessage]
    # 이전 턴에서 반환받은 필터 상태를 그대로 되돌려준다 — 첫 턴(None)이면
    # 라우터가 유저 프로필로 초기 필터를 만든다.
    filters: PolicyChatSearchInput | None = None
    include_closed: bool = False
    page_size: int = 10


class AiSearchMessageResponse(BaseModel):
    reply: str
    filters: PolicyChatSearchInput
    items: list[PolicyBrowseItem]
    total: int
    page: int
    page_size: int


class AiSearchResultsResponse(BaseModel):
    items: list[PolicyBrowseItem]
    total: int
    page: int
    page_size: int


class PolicyAnalysisRequest(BaseModel):
    policy_key: str


class PolicyAnalysisResponse(BaseModel):
    fit: Literal["적합", "부적합"]
    concerns: str | None = None
    benefit_summary: str
    application_notes: str
    required_documents: list[str] = []
    estimated_monthly_benefit_krw: int | None = None


class PolicyQaRequest(BaseModel):
    # 정책별 챗봇: 사용자가 지금 보고 있는 정책 하나에 대해서만 자유롭게 질문/답변한다
    # (ai_search/message의 필터 변경 챗봇과 달리 도구 호출 없이 순수 대화).
    policy_key: str
    messages: list[ChatMessage]


class PolicyQaResponse(BaseModel):
    reply: str
