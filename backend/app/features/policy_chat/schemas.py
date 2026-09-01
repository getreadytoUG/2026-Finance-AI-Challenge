from typing import Literal

from pydantic import BaseModel

from app.features.policy_matcher.categories import PolicyCategoryTag
from app.features.policy_matcher.matching import PolicyRegion
from app.features.policy_matcher.schemas import PolicyBrowseItem
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


FilterFieldName = Literal[
    "age",
    "is_married",
    "annual_income_krw",
    "spouse_annual_income_krw",
    "region",
    "keyword",
    "category",
    "status",
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
