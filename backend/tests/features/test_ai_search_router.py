import itertools
from datetime import datetime, timezone

from app.features.policy_chat import analysis as policy_chat_analysis
from app.features.policy_chat import router as policy_chat_router
from app.features.policy_matcher.models import CachedPolicy
from app.llm.base import LLMResponse, ToolCallRequest

_key_seq = itertools.count(1)


def _signup_login(client, email="ai-search-user@example.com", **overrides):
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
        policy_key=f"P{next(_key_seq)}",
        policy_name="테스트 정책",
        description="지원 내용 설명",
        apply_url="https://example.com",
        application_period="상시",
        apply_start_ymd=None,
        apply_end_ymd=None,
        min_age=None,
        max_age=None,
        min_income_krw=None,
        max_income_krw=None,
        marital_status="",
        region_code="",
        large_category="일자리",
        mid_category="",
        refreshed_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    row = CachedPolicy(**defaults)
    db_session.add(row)
    db_session.commit()
    return row


class _FakeProvider:
    def __init__(self, responses: list[LLMResponse]):
        self._responses = responses
        self.calls: list[tuple] = []

    def chat(self, messages, tools):
        self.calls.append((messages, tools))
        return self._responses[len(self.calls) - 1]


def test_ai_search_message_requires_auth(client):
    response = client.post("/policy_chat/ai_search/message", json={"messages": [{"role": "user", "content": "안녕"}]})
    assert response.status_code == 401


def test_ai_search_results_requires_auth(client):
    response = client.get("/policy_chat/ai_search/results")
    assert response.status_code == 401


def test_ai_search_message_first_turn_uses_profile_as_initial_filters(client, monkeypatch):
    token = _signup_login(client, age=33, is_married=True, region="부산")
    fake = _FakeProvider([LLMResponse(content="안녕하세요!", tool_calls=[])])
    monkeypatch.setattr(policy_chat_router, "get_provider", lambda: fake)

    response = client.post(
        "/policy_chat/ai_search/message",
        json={"messages": [{"role": "user", "content": "안녕"}], "filters": None},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["filters"]["age"] == 33
    assert body["filters"]["is_married"] is True
    assert body["filters"]["region"] == "부산"
    assert len(fake.calls) == 1  # tool_call 없으면 2차 호출 안 함


def test_ai_search_message_merges_only_changed_fields(client, db_session, monkeypatch):
    _seed_policy(db_session, region_code="26110")  # 부산
    token = _signup_login(client)
    fake = _FakeProvider(
        [
            LLMResponse(
                content=None,
                tool_calls=[ToolCallRequest(name="policy_ai_filter_delta", arguments={"region": "부산"})],
            ),
            LLMResponse(content="부산 정책을 찾았어요!", tool_calls=[]),
        ]
    )
    monkeypatch.setattr(policy_chat_router, "get_provider", lambda: fake)

    current_filters = {
        "age": 29,
        "is_married": False,
        "annual_income_krw": 40_000_000,
        "spouse_annual_income_krw": None,
        "region": "서울",
        "category": None,
        "keyword": "전세",
    }
    response = client.post(
        "/policy_chat/ai_search/message",
        json={"messages": [{"role": "user", "content": "부산으로 바꿔줘"}], "filters": current_filters},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    # region만 바뀌고, 나머지(keyword 등)는 기존 값 그대로 유지되어야 한다.
    assert body["filters"]["region"] == "부산"
    assert body["filters"]["age"] == 29
    assert body["filters"]["keyword"] == "전세"
    assert len(fake.calls) == 2


def test_ai_search_message_extracts_status_instead_of_free_text_keyword(client, db_session, monkeypatch):
    # 회귀 테스트: "곧 마감되는 공고만 보여줘" 같은 요청은 keyword로 잘못 담기면
    # (실제 정책명/설명에 그 문구가 없어) 조용히 0건이 된다 — status enum으로
    # 잡혀야 한다(2026-08-26 실사용 중 발견한 버그).
    token = _signup_login(client)
    fake = _FakeProvider(
        [
            LLMResponse(
                content=None,
                tool_calls=[ToolCallRequest(name="policy_ai_filter_delta", arguments={"status": "임박"})],
            ),
            LLMResponse(content="곧 마감되는 정책을 보여드릴게요!", tool_calls=[]),
        ]
    )
    monkeypatch.setattr(policy_chat_router, "get_provider", lambda: fake)

    response = client.post(
        "/policy_chat/ai_search/message",
        json={"messages": [{"role": "user", "content": "곧 마감되는 공고만 보여줘"}], "filters": None},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["filters"]["status"] == "임박"
    assert body["filters"]["keyword"] is None


def test_ai_search_message_ignores_delta_with_value_outside_enum(client, db_session, monkeypatch):
    # model_copy(update=...)는 검증을 건너뛰므로, 스키마 밖 값이 오면 라우터가
    # 직접 재검증해서 걸러내야 한다 — 걸러지면 이번 턴은 필터 변경 없이 유지된다.
    token = _signup_login(client)
    fake = _FakeProvider(
        [
            LLMResponse(
                content=None,
                tool_calls=[ToolCallRequest(name="policy_ai_filter_delta", arguments={"region": "강남구"})],
            ),
            LLMResponse(content="죄송해요, 서울 기준으로 계속 보여드릴게요.", tool_calls=[]),
        ]
    )
    monkeypatch.setattr(policy_chat_router, "get_provider", lambda: fake)

    current_filters = {
        "age": 29,
        "is_married": False,
        "annual_income_krw": 40_000_000,
        "spouse_annual_income_krw": None,
        "region": "서울",
        "category": None,
        "keyword": None,
        "status": None,
    }
    response = client.post(
        "/policy_chat/ai_search/message",
        json={"messages": [{"role": "user", "content": "강남구만 보여줘"}], "filters": current_filters},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["filters"]["region"] == "서울"


def test_ai_search_message_without_tool_call_keeps_filters_unchanged(client, db_session, monkeypatch):
    _seed_policy(db_session)
    token = _signup_login(client)
    fake = _FakeProvider([LLMResponse(content="어떤 조건을 찾으세요?", tool_calls=[])])
    monkeypatch.setattr(policy_chat_router, "get_provider", lambda: fake)

    current_filters = {
        "age": 29,
        "is_married": False,
        "annual_income_krw": 40_000_000,
        "spouse_annual_income_krw": None,
        "region": "서울",
        "category": None,
        "keyword": None,
        "status": None,
    }
    response = client.post(
        "/policy_chat/ai_search/message",
        json={"messages": [{"role": "user", "content": "안녕"}], "filters": current_filters},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["filters"] == current_filters
    assert response.json()["reply"] == "어떤 조건을 찾으세요?"


def test_ai_search_results_filters_by_query_params(client, db_session):
    _seed_policy(db_session, policy_name="서울 정책", region_code="11110")
    _seed_policy(db_session, policy_name="부산 정책", region_code="26110")
    token = _signup_login(client)

    response = client.get(
        "/policy_chat/ai_search/results",
        params={"region": "서울"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["policy_name"] == "서울 정책"


def test_ai_search_analyze_requires_auth(client):
    response = client.post("/policy_chat/ai_search/analyze", json={"policy_key": "P1"})
    assert response.status_code == 401


def test_ai_search_analyze_returns_404_for_unknown_policy(client):
    token = _signup_login(client)
    response = client.post(
        "/policy_chat/ai_search/analyze",
        json={"policy_key": "does-not-exist"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


def test_ai_search_analyze_calls_llm_once_and_returns_structured_result(client, db_session, monkeypatch):
    policy = _seed_policy(db_session, policy_name="청년 월세 지원")
    token = _signup_login(client)
    fake = _FakeProvider(
        [
            LLMResponse(
                content=None,
                tool_calls=[
                    ToolCallRequest(
                        name="policy_analysis_result",
                        arguments={
                            "fit": "적합",
                            "concerns": None,
                            "benefit_summary": "월 20만원 지원",
                            "application_notes": "재직 증명서를 준비하세요.",
                            "required_documents": ["재직증명서", "주민등록등본"],
                        },
                    )
                ],
            )
        ]
    )
    monkeypatch.setattr(policy_chat_analysis, "get_provider", lambda: fake)

    response = client.post(
        "/policy_chat/ai_search/analyze",
        json={"policy_key": policy.policy_key},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["fit"] == "적합"
    assert body["concerns"] is None
    assert body["benefit_summary"] == "월 20만원 지원"
    assert body["application_notes"] == "재직 증명서를 준비하세요."
    assert body["required_documents"] == ["재직증명서", "주민등록등본"]
    assert len(fake.calls) == 1


def test_ai_search_results_paginates(client, db_session):
    for i in range(12):
        _seed_policy(db_session, policy_name=f"정책{i}")
    token = _signup_login(client)

    response = client.get(
        "/policy_chat/ai_search/results",
        params={"page": 2, "page_size": 10},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 12
    assert len(body["items"]) == 2
    assert body["page"] == 2
