import json

import openai

from app.core.config import settings
from app.llm.base import LLMResponse, Message, ToolCallRequest
from app.tools.base import ToolSpec


def _to_openai_tools(tools: list[ToolSpec]) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.input_schema.model_json_schema(),
            },
        }
        for t in tools
    ]


class OpenAIProvider:
    def __init__(self) -> None:
        self._client = openai.OpenAI(api_key=settings.openai_api_key)

    def chat(self, messages: list[Message], tools: list[ToolSpec]) -> LLMResponse:
        response = self._client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            tools=_to_openai_tools(tools),
        )

        choice = response.choices[0].message
        tool_calls = [
            ToolCallRequest(name=tc.function.name, arguments=json.loads(tc.function.arguments))
            for tc in (choice.tool_calls or [])
        ]

        return LLMResponse(content=choice.content, tool_calls=tool_calls)
