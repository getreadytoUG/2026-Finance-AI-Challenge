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
