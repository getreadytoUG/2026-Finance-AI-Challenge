from app.features.policy_matcher import tool
from app.features.policy_matcher.categories import FINANCIAL_LARGE_CATEGORY
from app.features.policy_matcher.youth_center_client import RawYouthPolicy


def _signup_and_login(client, email="tools-user@example.com"):
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


def test_calling_registered_tool_returns_its_output(client, monkeypatch):
    # Mock fetch_policies to return a test policy without restricting conditions
    monkeypatch.setattr(
        tool,
        "fetch_all_policies",
        lambda: [
            RawYouthPolicy(
                policy_id="",
                policy_name="청년 전세자금대출 (테스트)",
                description="전세자금을 지원합니다",
                apply_url="https://www.example.com",
                application_period="상시",
                min_age=None,
                max_age=None,
                min_income_krw=None,
                max_income_krw=None,
                marital_status="",
                region_code="",
                large_category=FINANCIAL_LARGE_CATEGORY,
            )
        ],
    )
    token = _signup_and_login(client)
    response = client.post(
        "/tools/policy_matcher",
        json={"age": 29, "is_married": False, "annual_income_krw": 40_000_000, "region": "서울"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["options"][0]["policy_name"] == "청년 전세자금대출 (테스트)"


def test_calling_unknown_tool_returns_404(client):
    token = _signup_and_login(client, email="tools-user2@example.com")
    response = client.post("/tools/does_not_exist", json={}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404


def test_calling_tool_without_auth_returns_401(client):
    response = client.post("/tools/policy_matcher", json={})
    assert response.status_code == 401


def test_calling_tool_with_invalid_payload_returns_400(client):
    token = _signup_and_login(client, email="tools-user3@example.com")
    response = client.post("/tools/policy_matcher", json={"age": "not-a-number"}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 400


def test_all_feature_tools_are_registered(client):
    from app.tools.registry import registry

    assert {s.name for s in registry.all()} == {
        "policy_matcher",
        "policy_chat_search",
        "savings_planner",
        "subscription_report",
        "card_spending_report",
    }
