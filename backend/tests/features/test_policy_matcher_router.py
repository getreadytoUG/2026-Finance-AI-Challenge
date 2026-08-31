from datetime import datetime, timedelta, timezone

from app.auth.service import create_user
from app.core.security import create_access_token
from app.features.policy_matcher import ranking as marriage_ranking
from app.features.policy_matcher import recommender
from app.features.policy_matcher.categories import FINANCIAL_LARGE_CATEGORY
from app.features.policy_matcher.models import CachedPolicy
from app.features.policy_matcher.status import today_kst
from app.llm.base import LLMResponse, ToolCallRequest


def _signup_login_with_profile(client, email="router-user@example.com"):
    client.post(
        "/auth/signup",
        json={
            "email": email,
            "password": "secret123",
            "age": 29,
            "is_married": False,
            "annual_income_krw": 40_000_000,
            "region": "서울",
            "occupation": "employee",
        },
    )
    login = client.post("/auth/login", json={"email": email, "password": "secret123"})
    return login.json()["access_token"]


def _seed_policy(db_session, **overrides) -> CachedPolicy:
    defaults = dict(
        policy_key="P100",
        policy_name="테스트 정책",
        description="지원 내용",
        apply_url="https://example.com",
        application_period="상시",
        apply_start_ymd=None,
        apply_end_ymd=None,
        min_age=19,
        max_age=39,
        min_income_krw=None,
        max_income_krw=None,
        marital_status="",
        region_code="",
        large_category="기타",
        mid_category="",
        refreshed_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    row = CachedPolicy(**defaults)
    db_session.add(row)
    db_session.commit()
    return row


def test_refresh_requires_auth(client):
    response = client.post("/policy_matcher/recommendations/refresh")
    assert response.status_code == 401


def test_refresh_creates_recommendations_for_eligible_policies(client, db_session):
    _seed_policy(db_session)
    token = _signup_login_with_profile(client)
    response = client.post(
        "/policy_matcher/recommendations/refresh",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["created"] == 1


def test_refresh_returns_zero_when_profile_incomplete(client, db_session):
    _seed_policy(db_session)
    # 신규 회원가입은 이제 프로필을 항상 같이 받으므로, "프로필 미입력" 상태는
    # (데모 계정처럼) signup 스키마를 거치지 않은 유저로만 재현할 수 있다.
    user = create_user(db_session, "incomplete@example.com", "secret123")
    token = create_access_token(subject=str(user.id))
    response = client.post(
        "/policy_matcher/recommendations/refresh",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["created"] == 0


def test_refresh_failure_still_returns_cors_headers(client, db_session, monkeypatch):
    _seed_policy(db_session)

    def boom(policy, match_input):
        raise RuntimeError("boom")

    monkeypatch.setattr(recommender, "is_eligible", boom)
    token = _signup_login_with_profile(client)

    response = client.post(
        "/policy_matcher/recommendations/refresh",
        headers={"Authorization": f"Bearer {token}", "Origin": "http://localhost:3000"},
    )

    assert response.status_code == 500
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_list_returns_only_current_users_recommendations(client, db_session):
    _seed_policy(db_session, policy_key="P200")
    token_a = _signup_login_with_profile(client, email="user-a@example.com")
    client.post("/policy_matcher/recommendations/refresh", headers={"Authorization": f"Bearer {token_a}"})

    token_b = _signup_login_with_profile(client, email="user-b@example.com")

    response_b = client.get("/policy_matcher/recommendations", headers={"Authorization": f"Bearer {token_b}"})
    assert response_b.status_code == 200
    assert response_b.json()["recommendations"] == []

    response_a = client.get("/policy_matcher/recommendations", headers={"Authorization": f"Bearer {token_a}"})
    assert len(response_a.json()["recommendations"]) == 1
    assert response_a.json()["recommendations"][0]["policy_name"] == "테스트 정책"


def test_list_includes_unread_count(client, db_session):
    _seed_policy(db_session, policy_key="P300")
    token = _signup_login_with_profile(client)
    client.post("/policy_matcher/recommendations/refresh", headers={"Authorization": f"Bearer {token}"})

    response = client.get("/policy_matcher/recommendations", headers={"Authorization": f"Bearer {token}"})
    assert response.json()["unread_count"] == 1


def test_mark_recommendation_read_updates_is_read(client, db_session):
    _seed_policy(db_session, policy_key="P301")
    token = _signup_login_with_profile(client)
    client.post("/policy_matcher/recommendations/refresh", headers={"Authorization": f"Bearer {token}"})
    rec_id = client.get(
        "/policy_matcher/recommendations", headers={"Authorization": f"Bearer {token}"}
    ).json()["recommendations"][0]["id"]

    response = client.patch(
        f"/policy_matcher/recommendations/{rec_id}/read", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["is_read"] is True

    listing = client.get("/policy_matcher/recommendations", headers={"Authorization": f"Bearer {token}"})
    assert listing.json()["unread_count"] == 0


def test_list_recommendation_status_is_urgent_when_deadline_is_close(client, db_session):
    end = (today_kst() + timedelta(days=3)).strftime("%Y%m%d")
    _seed_policy(db_session, policy_key="P400", apply_end_ymd=end, application_period=f"~ {end}")
    token = _signup_login_with_profile(client)
    client.post("/policy_matcher/recommendations/refresh", headers={"Authorization": f"Bearer {token}"})

    response = client.get("/policy_matcher/recommendations", headers={"Authorization": f"Bearer {token}"})
    rec = response.json()["recommendations"][0]
    assert rec["status"] == "임박"
    assert rec["apply_end_ymd"] == end


def test_list_recommendation_status_is_상시_when_no_deadline(client, db_session):
    _seed_policy(db_session, policy_key="P401", apply_end_ymd=None)
    token = _signup_login_with_profile(client)
    client.post("/policy_matcher/recommendations/refresh", headers={"Authorization": f"Bearer {token}"})

    response = client.get("/policy_matcher/recommendations", headers={"Authorization": f"Bearer {token}"})
    rec = response.json()["recommendations"][0]
    assert rec["status"] == "상시"
    assert rec["apply_start_ymd"] is None
    assert rec["apply_end_ymd"] is None


def test_list_recommendation_falls_back_when_cached_policy_missing(client, db_session):
    _seed_policy(db_session, policy_key="P402")
    token = _signup_login_with_profile(client)
    client.post("/policy_matcher/recommendations/refresh", headers={"Authorization": f"Bearer {token}"})

    # cache.py는 실제로는 delete하지 않지만, 이론상 그런 상황이 와도 안전한지 검증한다.
    db_session.query(CachedPolicy).filter(CachedPolicy.policy_key == "P402").delete()
    db_session.commit()

    response = client.get("/policy_matcher/recommendations", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    rec = response.json()["recommendations"][0]
    assert rec["status"] == "상시"
    assert rec["apply_end_ymd"] is None


def test_marriage_comparison_requires_auth(client):
    response = client.post("/policy_matcher/marriage_comparison", json={"age": 29, "region": "서울", "annual_income_krw": 40_000_000})
    assert response.status_code == 401


def test_marriage_comparison_rejects_missing_required_fields(client, db_session):
    token = _signup_login_with_profile(client)
    response = client.post(
        "/policy_matcher/marriage_comparison",
        json={"age": 29},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


def test_marriage_comparison_returns_three_buckets(client, db_session):
    _seed_policy(
        db_session,
        policy_key="P500",
        max_income_krw=50_000_000,
        large_category=FINANCIAL_LARGE_CATEGORY,
    )
    token = _signup_login_with_profile(client)
    response = client.post(
        "/policy_matcher/marriage_comparison",
        json={
            "age": 29,
            "region": "서울",
            "annual_income_krw": 40_000_000,
            "spouse_annual_income_krw": 20_000_000,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert {"married_only", "unmarried_only", "both"} <= body.keys()
    assert [p["policy_key"] for p in body["unmarried_only"]] == ["P500"]


def test_marriage_comparison_rank_requires_auth(client):
    response = client.post(
        "/policy_matcher/marriage_comparison/rank",
        json={"age": 29, "region": "서울", "annual_income_krw": 40_000_000, "policy_keys": [], "context_label": "테스트"},
    )
    assert response.status_code == 401


class _FakeLLMProvider:
    def __init__(self, response: LLMResponse):
        self._response = response

    def chat(self, messages, tools):
        return self._response


def test_marriage_comparison_rank_reorders_by_llm_result(client, db_session, monkeypatch):
    _seed_policy(db_session, policy_key="P600", policy_name="일반 정책")
    _seed_policy(db_session, policy_key="P601", policy_name="신혼부부 특화 정책")
    token = _signup_login_with_profile(client)

    fake = _FakeLLMProvider(
        LLMResponse(
            content=None,
            tool_calls=[
                ToolCallRequest(
                    name="policy_ranking_result",
                    arguments={
                        "ranked": [
                            {"policy_key": "P601", "reason": "신혼부부 특화 정책이라 우선입니다."},
                            {"policy_key": "P600", "reason": "일반 대상 정책입니다."},
                        ]
                    },
                )
            ],
        )
    )
    monkeypatch.setattr(marriage_ranking, "get_provider", lambda: fake)

    response = client.post(
        "/policy_matcher/marriage_comparison/rank",
        json={
            "age": 29,
            "region": "서울",
            "annual_income_krw": 40_000_000,
            "policy_keys": ["P600", "P601"],
            "context_label": "혼인신고 후에만 자격되는 정책",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert [item["policy_key"] for item in body["ranked"]] == ["P601", "P600"]
    assert body["ranked"][0]["reason"] == "신혼부부 특화 정책이라 우선입니다."


def test_mark_recommendation_read_rejects_other_users_recommendation(client, db_session):
    _seed_policy(db_session, policy_key="P302")
    token_a = _signup_login_with_profile(client, email="read-a@example.com")
    client.post("/policy_matcher/recommendations/refresh", headers={"Authorization": f"Bearer {token_a}"})
    rec_id = client.get(
        "/policy_matcher/recommendations", headers={"Authorization": f"Bearer {token_a}"}
    ).json()["recommendations"][0]["id"]

    token_b = _signup_login_with_profile(client, email="read-b@example.com")
    response = client.patch(
        f"/policy_matcher/recommendations/{rec_id}/read", headers={"Authorization": f"Bearer {token_b}"}
    )
    assert response.status_code == 404
