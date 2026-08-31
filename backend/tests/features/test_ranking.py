from datetime import datetime, timezone

from app.features.policy_matcher import ranking
from app.features.policy_matcher.models import CachedPolicy
from app.features.policy_matcher.schemas import PolicyRankingInput
from app.llm.base import LLMResponse, ToolCallRequest


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


def _input(**overrides) -> PolicyRankingInput:
    defaults = dict(
        age=29,
        region="서울",
        annual_income_krw=40_000_000,
        policy_keys=["P1", "P2"],
        context_label="혼인신고 후에만 자격되는 정책",
    )
    defaults.update(overrides)
    return PolicyRankingInput(**defaults)


class _FakeProvider:
    def __init__(self, response: LLMResponse):
        self._response = response
        self.calls: list[tuple] = []

    def chat(self, messages, tools):
        self.calls.append((messages, tools))
        return self._response


def test_rank_policies_returns_llm_order_and_reasons(monkeypatch):
    fake = _FakeProvider(
        LLMResponse(
            content=None,
            tool_calls=[
                ToolCallRequest(
                    name="policy_ranking_result",
                    arguments={
                        "ranked": [
                            {"policy_key": "P2", "reason": "신혼부부 특화 정책이라 우선입니다."},
                            {"policy_key": "P1", "reason": "일반 청년 대상 정책입니다."},
                        ]
                    },
                )
            ],
        )
    )
    monkeypatch.setattr(ranking, "get_provider", lambda: fake)

    policies = [_policy(policy_key="P1"), _policy(policy_key="P2", policy_name="신혼부부 전세자금 대출")]
    result = ranking.rank_policies(_input(), policies)

    assert [item.policy_key for item in result.ranked] == ["P2", "P1"]
    assert result.ranked[0].reason == "신혼부부 특화 정책이라 우선입니다."
    assert len(fake.calls) == 1
    messages, tools = fake.calls[0]
    assert tools[0].name == "policy_ranking_result"
    assert "혼인신고 후에만 자격되는 정책" in messages[1].content
    assert "P1" in messages[1].content and "P2" in messages[1].content


def test_rank_policies_falls_back_when_no_tool_call(monkeypatch):
    fake = _FakeProvider(LLMResponse(content="텍스트로만 답했어요", tool_calls=[]))
    monkeypatch.setattr(ranking, "get_provider", lambda: fake)

    policies = [_policy(policy_key="P1"), _policy(policy_key="P2")]
    result = ranking.rank_policies(_input(), policies)

    assert [item.policy_key for item in result.ranked] == ["P1", "P2"]
    assert all("실패" in item.reason for item in result.ranked)


def test_rank_policies_falls_back_when_llm_drops_a_policy_key(monkeypatch):
    fake = _FakeProvider(
        LLMResponse(
            content=None,
            tool_calls=[
                ToolCallRequest(name="policy_ranking_result", arguments={"ranked": [{"policy_key": "P1", "reason": "..."}]})
            ],
        )
    )
    monkeypatch.setattr(ranking, "get_provider", lambda: fake)

    policies = [_policy(policy_key="P1"), _policy(policy_key="P2")]
    result = ranking.rank_policies(_input(), policies)

    assert [item.policy_key for item in result.ranked] == ["P1", "P2"]


def test_rank_policies_falls_back_when_llm_invents_an_unknown_policy_key(monkeypatch):
    fake = _FakeProvider(
        LLMResponse(
            content=None,
            tool_calls=[
                ToolCallRequest(
                    name="policy_ranking_result",
                    arguments={
                        "ranked": [
                            {"policy_key": "P1", "reason": "..."},
                            {"policy_key": "P999-NOT-REAL", "reason": "..."},
                        ]
                    },
                )
            ],
        )
    )
    monkeypatch.setattr(ranking, "get_provider", lambda: fake)

    policies = [_policy(policy_key="P1"), _policy(policy_key="P2")]
    result = ranking.rank_policies(_input(), policies)

    assert [item.policy_key for item in result.ranked] == ["P1", "P2"]


def test_rank_policies_returns_empty_when_no_policies_given(monkeypatch):
    fake = _FakeProvider(LLMResponse(content=None, tool_calls=[]))
    monkeypatch.setattr(ranking, "get_provider", lambda: fake)

    result = ranking.rank_policies(_input(policy_keys=[]), [])

    assert result.ranked == []
    assert len(fake.calls) == 0
