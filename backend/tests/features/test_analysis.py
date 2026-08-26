from datetime import datetime, timezone

from app.auth.models import User
from app.features.policy_chat import analysis
from app.features.policy_matcher.models import CachedPolicy
from app.llm.base import LLMResponse


def _user(**overrides) -> User:
    defaults = dict(
        id=1,
        email="a@example.com",
        hashed_password="x",
        age=29,
        is_married=False,
        annual_income_krw=40_000_000,
        region="서울",
    )
    defaults.update(overrides)
    return User(**defaults)


def _policy(**overrides) -> CachedPolicy:
    defaults = dict(
        policy_key="P1",
        policy_name="청년 월세 지원",
        description="월 20만원 지원",
        apply_url="https://example.com",
        application_period="상시",
        apply_start_ymd=None,
        apply_end_ymd=None,
        min_age=19,
        max_age=34,
        min_income_krw=None,
        max_income_krw=26_000_000,
        marital_status="",
        region_code="",
        large_category="주거",
        mid_category="",
        refreshed_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return CachedPolicy(**defaults)


class _FakeProvider:
    def __init__(self, response: LLMResponse):
        self._response = response
        self.calls: list[tuple] = []

    def chat(self, messages, tools):
        self.calls.append((messages, tools))
        return self._response


def test_generate_policy_report_calls_llm_once_with_no_tools(monkeypatch):
    fake = _FakeProvider(LLMResponse(content="적합도: 조건부 적합\n예상 혜택: ...", tool_calls=[]))
    monkeypatch.setattr(analysis, "get_provider", lambda: fake)

    report = analysis.generate_policy_report(_user(), _policy())

    assert report == "적합도: 조건부 적합\n예상 혜택: ..."
    assert len(fake.calls) == 1
    messages, tools = fake.calls[0]
    assert tools == []
    assert messages[0].role == "system"
    assert "청년 월세 지원" in messages[1].content
    assert "29세" in messages[1].content


def test_generate_policy_report_falls_back_when_llm_returns_no_content(monkeypatch):
    fake = _FakeProvider(LLMResponse(content=None, tool_calls=[]))
    monkeypatch.setattr(analysis, "get_provider", lambda: fake)

    report = analysis.generate_policy_report(_user(), _policy())

    assert report == "분석 결과를 생성하지 못했습니다."
