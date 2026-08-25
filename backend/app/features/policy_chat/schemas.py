from typing import Literal

from pydantic import BaseModel


class PolicyChatSearchInput(BaseModel):
    # 자연어 질의는 조건을 다 언급하지 않는 경우가 많다 — 언급 안 된 필드는
    # router에서 사용자 프로필 기본값으로 채운 뒤 이 스키마로 넘어온다.
    age: int | None = None
    is_married: bool | None = None
    annual_income_krw: int | None = None
    spouse_annual_income_krw: int | None = None
    region: str | None = None
    keyword: str | None = None


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
