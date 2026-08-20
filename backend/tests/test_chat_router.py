from pydantic import BaseModel

from app.llm.base import LLMResponse, ToolCallRequest
from app.llm.chat_router import get_llm_provider
from app.main import app
from app.tools.base import ToolContext, ToolSpec
from app.tools.registry import ToolRegistry, get_tool_registry


class EchoInput(BaseModel):
    text: str


class EchoOutput(BaseModel):
    echoed: str


def _echo_run(input: EchoInput, ctx: ToolContext) -> EchoOutput:
    return EchoOutput(echoed=input.text)


def _test_registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(
        ToolSpec(
            name="echo_tool",
            description="echoes text back",
            input_schema=EchoInput,
            output_schema=EchoOutput,
            entrypoint=_echo_run,
        )
    )
    return reg


class FakeProvider:
    def __init__(self, responses: list[LLMResponse]):
        self._responses = iter(responses)

    def chat(self, messages, tools):
        return next(self._responses)


def _login(client) -> str:
    client.post("/auth/signup", json={"email": "chat-user@example.com", "password": "secret123"})
    login = client.post("/auth/login", json={"email": "chat-user@example.com", "password": "secret123"})
    return login.json()["access_token"]


def test_chat_returns_direct_content_when_no_tool_call(client):
    token = _login(client)
    app.dependency_overrides[get_llm_provider] = lambda: FakeProvider(
        [LLMResponse(content="안녕하세요!", tool_calls=[])]
    )
    app.dependency_overrides[get_tool_registry] = _test_registry

    response = client.post("/chat", json={"message": "hi"}, headers={"Authorization": f"Bearer {token}"})

    app.dependency_overrides.pop(get_llm_provider, None)
    app.dependency_overrides.pop(get_tool_registry, None)

    assert response.status_code == 200
    assert response.json()["reply"] == "안녕하세요!"


def test_chat_executes_tool_call_then_returns_final_content(client):
    token = _login(client)
    app.dependency_overrides[get_llm_provider] = lambda: FakeProvider(
        [
            LLMResponse(content=None, tool_calls=[ToolCallRequest(name="echo_tool", arguments={"text": "hello"})]),
            LLMResponse(content="done", tool_calls=[]),
        ]
    )
    app.dependency_overrides[get_tool_registry] = _test_registry

    response = client.post("/chat", json={"message": "please echo hello"}, headers={"Authorization": f"Bearer {token}"})

    app.dependency_overrides.pop(get_llm_provider, None)
    app.dependency_overrides.pop(get_tool_registry, None)

    assert response.status_code == 200
    assert response.json()["reply"] == "done"


def test_chat_requires_auth(client):
    response = client.post("/chat", json={"message": "hi"})
    assert response.status_code == 401


def test_chat_recovers_when_tool_call_has_invalid_arguments(client):
    token = _login(client)
    app.dependency_overrides[get_llm_provider] = lambda: FakeProvider(
        [
            # "text" is required by EchoInput but omitted here — must not 500.
            LLMResponse(content=None, tool_calls=[ToolCallRequest(name="echo_tool", arguments={})]),
            LLMResponse(content="recovered", tool_calls=[]),
        ]
    )
    app.dependency_overrides[get_tool_registry] = _test_registry

    response = client.post("/chat", json={"message": "please echo hello"}, headers={"Authorization": f"Bearer {token}"})

    app.dependency_overrides.pop(get_llm_provider, None)
    app.dependency_overrides.pop(get_tool_registry, None)

    assert response.status_code == 200
    assert response.json()["reply"] == "recovered"
