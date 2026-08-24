def test_signup_creates_user(client):
    response = client.post("/auth/signup", json={"email": "a@example.com", "password": "secret123"})
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "a@example.com"
    assert "id" in body
    assert "password" not in body


def test_signup_duplicate_email_returns_400(client):
    client.post("/auth/signup", json={"email": "dup@example.com", "password": "secret123"})
    response = client.post("/auth/signup", json={"email": "dup@example.com", "password": "other456"})
    assert response.status_code == 400


def test_login_with_correct_credentials_returns_token(client):
    client.post("/auth/signup", json={"email": "b@example.com", "password": "secret123"})
    response = client.post("/auth/login", json={"email": "b@example.com", "password": "secret123"})
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_with_wrong_password_returns_401(client):
    client.post("/auth/signup", json={"email": "c@example.com", "password": "secret123"})
    response = client.post("/auth/login", json={"email": "c@example.com", "password": "wrong"})
    assert response.status_code == 401


def test_protected_route_requires_token(client):
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_protected_route_returns_current_user_with_valid_token(client):
    client.post("/auth/signup", json={"email": "d@example.com", "password": "secret123"})
    login = client.post("/auth/login", json={"email": "d@example.com", "password": "secret123"})
    token = login.json()["access_token"]
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "d@example.com"


def test_update_profile_sets_fields_and_returns_them(client):
    client.post("/auth/signup", json={"email": "e@example.com", "password": "secret123"})
    login = client.post("/auth/login", json={"email": "e@example.com", "password": "secret123"})
    token = login.json()["access_token"]
    response = client.put(
        "/auth/profile",
        json={"age": 29, "is_married": False, "annual_income_krw": 40_000_000, "region": "서울"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["age"] == 29
    assert body["is_married"] is False
    assert body["annual_income_krw"] == 40_000_000
    assert body["region"] == "서울"


def test_update_profile_requires_auth(client):
    response = client.put(
        "/auth/profile",
        json={"age": 29, "is_married": False, "annual_income_krw": 40_000_000, "region": "서울"},
    )
    assert response.status_code == 401


def test_me_reflects_profile_after_update(client):
    client.post("/auth/signup", json={"email": "f@example.com", "password": "secret123"})
    login = client.post("/auth/login", json={"email": "f@example.com", "password": "secret123"})
    token = login.json()["access_token"]
    client.put(
        "/auth/profile",
        json={"age": 31, "is_married": True, "annual_income_krw": 55_000_000, "region": "부산"},
        headers={"Authorization": f"Bearer {token}"},
    )
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.json()["region"] == "부산"


def test_me_returns_null_profile_fields_before_update(client):
    client.post("/auth/signup", json={"email": "g@example.com", "password": "secret123"})
    login = client.post("/auth/login", json={"email": "g@example.com", "password": "secret123"})
    token = login.json()["access_token"]
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    body = response.json()
    assert body["age"] is None
    assert body["is_married"] is None
    assert body["annual_income_krw"] is None
    assert body["region"] is None


def test_seed_demo_user_creates_a_working_login(client, db_session):
    from app.auth.service import DEMO_USER_EMAIL, DEMO_USER_PASSWORD, seed_demo_user

    seed_demo_user(db_session)

    response = client.post(
        "/auth/login", json={"email": DEMO_USER_EMAIL, "password": DEMO_USER_PASSWORD}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_seed_demo_user_is_idempotent(client, db_session):
    from app.auth.service import seed_demo_user

    seed_demo_user(db_session)
    seed_demo_user(db_session)  # 두 번째 호출은 조용히 아무것도 안 해야 한다

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {_login_as_demo(client)}"})
    assert response.status_code == 200


def _login_as_demo(client) -> str:
    from app.auth.service import DEMO_USER_EMAIL, DEMO_USER_PASSWORD

    response = client.post(
        "/auth/login", json={"email": DEMO_USER_EMAIL, "password": DEMO_USER_PASSWORD}
    )
    return response.json()["access_token"]
