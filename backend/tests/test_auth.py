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


def test_check_email_available_for_unregistered_email(client):
    response = client.get("/auth/check-email", params={"email": "new@example.com"})
    assert response.status_code == 200
    assert response.json() == {"available": True}


def test_check_email_unavailable_for_registered_email(client):
    client.post("/auth/signup", json=_signup_payload("taken@example.com"))
    response = client.get("/auth/check-email", params={"email": "taken@example.com"})
    assert response.status_code == 200
    assert response.json() == {"available": False}


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


def test_token_issued_before_a_restart_is_rejected_after_restart(client, monkeypatch):
    # 재배포/재시작으로 서버 프로세스가 새로 뜨면 BOOT_ID가 바뀌고, 그 전에
    # 발급된 토큰은 전부 무효 처리되어 강제 로그아웃돼야 한다(재로그인은 가능).
    from app.core import security

    client.post("/auth/signup", json=_signup_payload("restart-test@example.com"))
    login = client.post(
        "/auth/login", json={"email": "restart-test@example.com", "password": "secret123"}
    )
    token = login.json()["access_token"]

    monkeypatch.setattr(security, "BOOT_ID", "simulated-new-deploy-boot-id")

    stale_response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert stale_response.status_code == 401

    relogin = client.post(
        "/auth/login", json={"email": "restart-test@example.com", "password": "secret123"}
    )
    assert relogin.status_code == 200
    fresh_response = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {relogin.json()['access_token']}"}
    )
    assert fresh_response.status_code == 200


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


def test_seed_admin_user_creates_admin_once_and_is_idempotent(db_session):
    from app.auth.models import User
    from app.auth.service import seed_admin_user
    from app.core.config import settings

    seed_admin_user(db_session)
    seed_admin_user(db_session)  # 두 번째 호출은 이미 존재하니 아무 것도 안 해야 한다

    admins = db_session.query(User).filter(User.email == settings.admin_email).all()
    assert len(admins) == 1


def test_admin_account_can_log_in_with_seeded_credentials(client, db_session):
    from app.auth.service import seed_admin_user
    from app.core.config import settings

    seed_admin_user(db_session)
    response = client.post(
        "/auth/login", json={"email": settings.admin_email, "password": settings.admin_password}
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


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


