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


def test_signup_creates_user(client):
    response = client.post("/auth/signup", json=_signup_payload("a@example.com"))
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "a@example.com"
    assert body["age"] == 29
    assert body["occupation"] == "employee"
    assert "id" in body
    assert "password" not in body


def test_signup_stores_spouse_info_when_married(client):
    response = client.post(
        "/auth/signup",
        json=_signup_payload(
            "married@example.com",
            is_married=True,
            spouse_age=31,
            spouse_annual_income_krw=35_000_000,
            spouse_occupation="student",
        ),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["spouse_age"] == 31
    assert body["spouse_annual_income_krw"] == 35_000_000
    assert body["spouse_occupation"] == "student"


def test_signup_without_spouse_info_defaults_to_null(client):
    response = client.post("/auth/signup", json=_signup_payload("nospouse@example.com"))
    assert response.status_code == 201
    body = response.json()
    assert body["spouse_age"] is None
    assert body["spouse_annual_income_krw"] is None
    assert body["spouse_occupation"] is None


def test_signup_missing_required_profile_field_returns_422(client):
    payload = _signup_payload("incomplete@example.com")
    del payload["age"]
    response = client.post("/auth/signup", json=payload)
    assert response.status_code == 422


def test_signup_duplicate_email_returns_400(client):
    client.post("/auth/signup", json=_signup_payload("dup@example.com"))
    response = client.post("/auth/signup", json=_signup_payload("dup@example.com"))
    assert response.status_code == 400


def test_login_with_correct_credentials_returns_token(client):
    client.post("/auth/signup", json=_signup_payload("b@example.com"))
    response = client.post("/auth/login", json={"email": "b@example.com", "password": "secret123"})
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_with_wrong_password_returns_401(client):
    client.post("/auth/signup", json=_signup_payload("c@example.com"))
    response = client.post("/auth/login", json={"email": "c@example.com", "password": "wrong"})
    assert response.status_code == 401


def test_protected_route_requires_token(client):
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_protected_route_returns_current_user_with_valid_token(client):
    client.post("/auth/signup", json=_signup_payload("d@example.com"))
    login = client.post("/auth/login", json={"email": "d@example.com", "password": "secret123"})
    token = login.json()["access_token"]
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "d@example.com"


def _profile_payload(**overrides) -> dict:
    payload = {
        "age": 29,
        "is_married": False,
        "annual_income_krw": 40_000_000,
        "region": "서울",
        "occupation": "employee",
    }
    payload.update(overrides)
    return payload


def test_update_profile_sets_fields_and_returns_them(client):
    client.post("/auth/signup", json=_signup_payload("e@example.com"))
    login = client.post("/auth/login", json={"email": "e@example.com", "password": "secret123"})
    token = login.json()["access_token"]
    response = client.put(
        "/auth/profile",
        json=_profile_payload(age=30, region="부산", occupation="self_employed"),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["age"] == 30
    assert body["is_married"] is False
    assert body["annual_income_krw"] == 40_000_000
    assert body["region"] == "부산"
    assert body["occupation"] == "self_employed"


def test_update_profile_sets_and_clears_spouse_info(client):
    client.post("/auth/signup", json=_signup_payload("spouse-update@example.com"))
    login = client.post(
        "/auth/login", json={"email": "spouse-update@example.com", "password": "secret123"}
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    married = client.put(
        "/auth/profile",
        json=_profile_payload(
            is_married=True,
            spouse_age=33,
            spouse_annual_income_krw=45_000_000,
            spouse_occupation="employee",
        ),
        headers=headers,
    )
    assert married.json()["spouse_age"] == 33

    unmarried_again = client.put(
        "/auth/profile",
        json=_profile_payload(is_married=False),
        headers=headers,
    )
    assert unmarried_again.json()["spouse_age"] is None


def test_update_profile_requires_auth(client):
    response = client.put("/auth/profile", json=_profile_payload())
    assert response.status_code == 401


def test_me_reflects_profile_after_update(client):
    client.post("/auth/signup", json=_signup_payload("f@example.com"))
    login = client.post("/auth/login", json={"email": "f@example.com", "password": "secret123"})
    token = login.json()["access_token"]
    client.put(
        "/auth/profile",
        json=_profile_payload(age=31, is_married=True, annual_income_krw=55_000_000, region="부산"),
        headers={"Authorization": f"Bearer {token}"},
    )
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.json()["region"] == "부산"


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


def test_seed_demo_user_has_null_profile_fields(client, db_session):
    from app.auth.service import seed_demo_user

    seed_demo_user(db_session)

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {_login_as_demo(client)}"})
    body = response.json()
    assert body["age"] is None
    assert body["is_married"] is None
    assert body["annual_income_krw"] is None
    assert body["region"] is None
    assert body["occupation"] is None


def _login_as_demo(client) -> str:
    from app.auth.service import DEMO_USER_EMAIL, DEMO_USER_PASSWORD

    response = client.post(
        "/auth/login", json={"email": DEMO_USER_EMAIL, "password": DEMO_USER_PASSWORD}
    )
    return response.json()["access_token"]
