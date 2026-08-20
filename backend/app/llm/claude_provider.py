import anthropic

from app.core.config import settings
from app.llm.base import LLMResponse, Message, ToolCallRequest
from app.tools.base import ToolSpec


def _to_claude_tools(tools: list[ToolSpec]) -> list[dict]:
    return [
        {
            "name": t.name,
            "description": t.description,
            "input_schema": t.input_schema.model_json_schema(),
        }
        for t in tools
    ]


class ClaudeProvider:
    def __init__(self) -> None:
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def chat(self, messages: list[Message], tools: list[ToolSpec]) -> LLMResponse:
        system_messages = [m.content for m in messages if m.role == "system"]
        conversation = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]

        response = self._client.messages.create(
            model=settings.claude_model,
            max_tokens=1024,
            system=system_messages[0] if system_messages else None,
            messages=conversation,
            tools=_to_claude_tools(tools),
        )

        content_text: str | None = None
        tool_calls: list[ToolCallRequest] = []
        for block in response.content:
            if block.type == "text":
                content_text = block.text
            elif block.type == "tool_use":
                tool_calls.append(ToolCallRequest(name=block.name, arguments=block.input))

        return LLMResponse(content=content_text, tool_calls=tool_calls)
