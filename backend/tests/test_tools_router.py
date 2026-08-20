def _signup_and_login(client, email="tools-user@example.com"):
    client.post("/auth/signup", json={"email": email, "password": "secret123"})
    login = client.post("/auth/login", json={"email": email, "password": "secret123"})
    return login.json()["access_token"]


def test_calling_registered_tool_returns_its_output(client):
    token = _signup_and_login(client)
    response = client.post(
        "/tools/policy_matcher",
        json={"age": 29, "is_married": False, "annual_income_krw": 40_000_000, "region": "서울"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["options"][0]["eligible"] is True


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
