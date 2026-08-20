from typing import Literal, Protocol

from pydantic import BaseModel

from app.tools.base import ToolSpec


class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ToolCallRequest(BaseModel):
    name: str
    arguments: dict


class LLMResponse(BaseModel):
    content: str | None = None
    tool_calls: list[ToolCallRequest] = []


class LLMProvider(Protocol):
    def chat(self, messages: list[Message], tools: list[ToolSpec]) -> LLMResponse: ...
