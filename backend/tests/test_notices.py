from app.features.notices.router import seed_example_notices_if_empty


def _signup_payload(email: str, **overrides) -> dict:
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
    return payload


def _login_after_signup(client, email: str) -> str:
    client.post("/auth/signup", json=_signup_payload(email))
    response = client.post("/auth/login", json={"email": email, "password": "secret123"})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_list_notices_requires_auth(client):
    response = client.get("/notices")
    assert response.status_code == 401


def test_list_notices_returns_seeded_examples(client, db_session):
    seed_example_notices_if_empty(db_session)
    token = _login_after_signup(client, "notices-user@example.com")

    response = client.get("/notices", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    body = response.json()
    assert len(body["notices"]) == 5
    # 최신순 정렬(seed 데이터의 days_ago가 가장 작은 항목이 먼저 나와야 함)
    created_ats = [n["created_at"] for n in body["notices"]]
    assert created_ats == sorted(created_ats, reverse=True)
    categories = {n["category"] for n in body["notices"]}
    assert "금리" in categories
    assert "상품" in categories


def test_list_notices_is_empty_without_seed(client, db_session):
    token = _login_after_signup(client, "empty-notices@example.com")
    response = client.get("/notices", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["notices"] == []
