from datetime import datetime, timezone

from app.features.policy_chat import router as policy_chat_router
from app.features.policy_matcher.categories import FINANCIAL_LARGE_CATEGORY
from app.features.policy_matcher.models import CachedPolicy
from app.llm.base import LLMResponse, ToolCallRequest


def _signup_login(client, email="chat-user@example.com", **overrides):
    payload = {
        "email": email,
        "password": "secret123",
        "age": 29,
        "is_married": False,
        "annual_income_krw": 40_000_000,
        "region": "서울",
        "occupation": "employee",
    }
    payload.update(overrides)
    client.post("/auth/signup", json=payload)
    login = client.post("/auth/login", json={"email": email, "password": "secret123"})
    return login.json()["access_token"]


def _seed_policy(db_session, **overrides) -> CachedPolicy:
    defaults = dict(
        policy_key="chat-p1",
        policy_name="테스트 정책",
        description="지원 내용 설명",
        apply_url="https://www.youthcenter.go.kr",
        application_period="상시",
        apply_start_ymd=None,
        apply_end_ymd=None,
        min_age=None,
        max_age=None,
        min_income_krw=None,
        max_income_krw=None,
        marital_status="",
        region_code="",
        large_category=FINANCIAL_LARGE_CATEGORY,
        mid_category="",
        refreshed_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    row = CachedPolicy(**defaults)
    db_session.add(row)
    db_session.commit()
    return row


class _FakeProvider:
    """호출 순서대로 미리 정해둔 LLMResponse를 하나씩 돌려주는 테스트용 provider."""

    def __init__(self, responses: list[LLMResponse]):
        self._responses = responses
        self.calls: list[tuple] = []

    def chat(self, messages, tools):
        self.calls.append((messages, tools))
        return self._responses[len(self.calls) - 1]


def test_message_requires_auth(client):
    response = client.post("/policy_chat/message", json={"messages": [{"role": "user", "content": "안녕"}]})
    assert response.status_code == 401


def test_message_returns_direct_reply_when_model_does_not_call_tool(client, monkeypatch):
    token = _signup_login(client)
    fake = _FakeProvider([LLMResponse(content="안녕하세요! 무엇을 도와드릴까요?", tool_calls=[])])
    monkeypatch.setattr(policy_chat_router, "get_provider", lambda: fake)

    response = client.post(
        "/policy_chat/message",
        json={"messages": [{"role": "user", "content": "안녕"}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == "안녕하세요! 무엇을 도와드릴까요?"
    assert body["policies"] == []
    assert len(fake.calls) == 1  # tool_call이 없으면 2차 호출을 하지 않는다


def test_message_executes_tool_and_returns_policies(client, db_session, monkeypatch):
    token = _signup_login(client)
    _seed_policy(db_session, policy_name="전세자금 대출")

    fake = _FakeProvider(
        [
            LLMResponse(
                content=None,
                tool_calls=[ToolCallRequest(name="policy_chat_search", arguments={"keyword": "전세"})],
            ),
            LLMResponse(content="전세자금 대출 정책을 찾았어요!", tool_calls=[]),
        ]
    )
    monkeypatch.setattr(policy_chat_router, "get_provider", lambda: fake)

    response = client.post(
        "/policy_chat/message",
        json={"messages": [{"role": "user", "content": "전세자금 대출 관련 정책 있어?"}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == "전세자금 대출 정책을 찾았어요!"
    assert len(body["policies"]) == 1
    assert body["policies"][0]["policy_name"] == "전세자금 대출"
    assert len(fake.calls) == 2


def test_message_fills_in_missing_args_from_user_profile(client, db_session, monkeypatch):
    token = _signup_login(client, email="profile-fill@example.com", age=33, region="부산")
    _seed_policy(db_session, region_code="26110")

    fake = _FakeProvider(
        [
            # 모델이 region을 언급하지 않았어도, router가 유저 프로필의 region("부산")을 채워 넣어야 한다.
            LLMResponse(content=None, tool_calls=[ToolCallRequest(name="policy_chat_search", arguments={})]),
            LLMResponse(content="부산 정책을 찾았어요!", tool_calls=[]),
        ]
    )
    monkeypatch.setattr(policy_chat_router, "get_provider", lambda: fake)

    response = client.post(
        "/policy_chat/message",
        json={"messages": [{"role": "user", "content": "지원되는 정책 있어?"}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert len(response.json()["policies"]) == 1
