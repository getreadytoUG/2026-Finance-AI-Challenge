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

        create_kwargs: dict = {
            "model": settings.claude_model,
            "max_tokens": 1024,
            "messages": conversation,
            "tools": _to_claude_tools(tools),
        }
        if system_messages:
            # The Anthropic SDK's `system` param must be omitted entirely when
            # absent — passing `system=None` sends a literal null the API rejects.
            create_kwargs["system"] = system_messages[0]

        response = self._client.messages.create(**create_kwargs)

        content_text: str | None = None
        tool_calls: list[ToolCallRequest] = []
        for block in response.content:
            if block.type == "text":
                content_text = block.text
            elif block.type == "tool_use":
                tool_calls.append(ToolCallRequest(name=block.name, arguments=block.input))

        return LLMResponse(content=content_text, tool_calls=tool_calls)
