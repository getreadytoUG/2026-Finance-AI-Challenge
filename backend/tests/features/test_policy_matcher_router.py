from app.auth.service import create_user
from app.core.security import create_access_token
from app.features.policy_matcher import recommender
from app.features.policy_matcher.youth_center_client import RawYouthPolicy


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


def _policy(**overrides) -> RawYouthPolicy:
    defaults = dict(
        policy_id="P100",
        policy_name="테스트 정책",
        description="지원 내용",
        apply_url="https://example.com",
        application_period="상시",
        min_age=None,
        max_age=None,
        min_income_krw=None,
        max_income_krw=None,
        marital_status="",
        region_code="",
    )
    defaults.update(overrides)
    return RawYouthPolicy(**defaults)


def test_refresh_requires_auth(client):
    response = client.post("/policy_matcher/recommendations/refresh")
    assert response.status_code == 401


def test_refresh_creates_recommendations_for_eligible_policies(client, monkeypatch):
    monkeypatch.setattr(recommender, "fetch_all_policies", lambda: [_policy()])
    token = _signup_login_with_profile(client)
    response = client.post(
        "/policy_matcher/recommendations/refresh",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["created"] == 1


def test_refresh_returns_zero_when_profile_incomplete(client, db_session, monkeypatch):
    monkeypatch.setattr(recommender, "fetch_all_policies", lambda: [_policy()])
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


def test_refresh_failure_still_returns_cors_headers(client, monkeypatch):
    def boom():
        raise RuntimeError("boom")

    monkeypatch.setattr(recommender, "fetch_all_policies", boom)
    token = _signup_login_with_profile(client)

    response = client.post(
        "/policy_matcher/recommendations/refresh",
        headers={"Authorization": f"Bearer {token}", "Origin": "http://localhost:3000"},
    )

    assert response.status_code == 500
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_list_returns_only_current_users_recommendations(client, monkeypatch):
    monkeypatch.setattr(recommender, "fetch_all_policies", lambda: [_policy(policy_id="P200")])
    token_a = _signup_login_with_profile(client, email="user-a@example.com")
    client.post("/policy_matcher/recommendations/refresh", headers={"Authorization": f"Bearer {token_a}"})

    token_b = _signup_login_with_profile(client, email="user-b@example.com")

    response_b = client.get("/policy_matcher/recommendations", headers={"Authorization": f"Bearer {token_b}"})
    assert response_b.status_code == 200
    assert response_b.json()["recommendations"] == []

    response_a = client.get("/policy_matcher/recommendations", headers={"Authorization": f"Bearer {token_a}"})
    assert len(response_a.json()["recommendations"]) == 1
    assert response_a.json()["recommendations"][0]["policy_name"] == "테스트 정책"


def test_list_includes_unread_count(client, monkeypatch):
    monkeypatch.setattr(recommender, "fetch_all_policies", lambda: [_policy(policy_id="P300")])
    token = _signup_login_with_profile(client)
    client.post("/policy_matcher/recommendations/refresh", headers={"Authorization": f"Bearer {token}"})

    response = client.get("/policy_matcher/recommendations", headers={"Authorization": f"Bearer {token}"})
    assert response.json()["unread_count"] == 1


def test_mark_recommendation_read_updates_is_read(client, monkeypatch):
    monkeypatch.setattr(recommender, "fetch_all_policies", lambda: [_policy(policy_id="P301")])
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


def test_mark_recommendation_read_rejects_other_users_recommendation(client, monkeypatch):
    monkeypatch.setattr(recommender, "fetch_all_policies", lambda: [_policy(policy_id="P302")])
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
