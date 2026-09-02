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


def test_signup_rejects_unrealistically_large_annual_income_with_422(client):
    # 2026-09-02 QA에서 발견: 연소득에 999999999999(만원)를 넣으면 원 단위로 환산한
    # 값이 users.annual_income_krw(Postgres 32비트 integer) 범위를 넘겨서 INSERT가
    # DataError로 죽고, 그게 uncaught exception이라 CORS를 못 거치는 500으로 빠져
    # 브라우저에는 "Failed to fetch"만 떴다. 이제 스키마 검증(le=2,000,000,000)이
    # DB에 닿기 전에 명확한 422로 막아야 한다.
    response = client.post("/auth/signup", json=_signup_payload("huge-income@example.com", annual_income_krw=9_999_999_999_990_000))
    assert response.status_code == 422


def test_signup_rejects_unrealistically_large_net_worth_with_422(client):
    response = client.post(
        "/auth/signup", json=_signup_payload("huge-networth@example.com", net_worth_krw=9_999_999_999_990_000)
    )
    assert response.status_code == 422


def test_signup_accepts_annual_income_at_the_upper_bound(client):
    response = client.post("/auth/signup", json=_signup_payload("max-income@example.com", annual_income_krw=2_000_000_000))
    assert response.status_code == 201


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


def test_delete_account_requires_auth(client):
    response = client.request("DELETE", "/auth/me", json={"password": "secret123"})
    assert response.status_code == 401


def test_delete_account_rejects_wrong_password(client):
    client.post("/auth/signup", json=_signup_payload("wrong-pw-delete@example.com"))
    login = client.post("/auth/login", json={"email": "wrong-pw-delete@example.com", "password": "secret123"})
    token = login.json()["access_token"]

    response = client.request(
        "DELETE",
        "/auth/me",
        json={"password": "not-the-password"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403

    # 삭제 안 됐으니 여전히 로그인 가능해야 한다.
    relogin = client.post("/auth/login", json={"email": "wrong-pw-delete@example.com", "password": "secret123"})
    assert relogin.status_code == 200


def test_delete_account_rejects_missing_password(client):
    client.post("/auth/signup", json=_signup_payload("missing-pw-delete@example.com"))
    login = client.post("/auth/login", json={"email": "missing-pw-delete@example.com", "password": "secret123"})
    token = login.json()["access_token"]

    response = client.request("DELETE", "/auth/me", json={}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_delete_account_with_correct_password_removes_user_and_data(client, db_session):
    from app.auth.models import User
    from app.features.policy_matcher.models import CachedPolicy, PolicyRecommendation
    from app.features.savings_planner.models import SavingsLinkedBenefit
    from datetime import datetime, timezone

    signup = client.post("/auth/signup", json=_signup_payload("delete-me@example.com"))
    user_id = signup.json()["id"]
    login = client.post("/auth/login", json={"email": "delete-me@example.com", "password": "secret123"})
    token = login.json()["access_token"]

    # 이 유저를 참조하는 다른 feature 테이블에도 데이터를 남겨서, 탈퇴 시 같이
    # 지워지는지 검증한다.
    db_session.add(
        CachedPolicy(
            policy_key="DEL-P1",
            policy_name="테스트 정책",
            description="설명",
            apply_url="https://example.com",
            application_period="상시",
            large_category="기타",
            mid_category="",
            marital_status="",
            region_code="",
            refreshed_at=datetime.now(timezone.utc),
        )
    )
    db_session.add(
        PolicyRecommendation(
            user_id=user_id,
            policy_key="DEL-P1",
            policy_name="테스트 정책",
            benefit_description="설명",
            application_period="상시",
            reference_url="https://example.com",
            matched_at=datetime.now(timezone.utc),
        )
    )
    db_session.add(
        SavingsLinkedBenefit(
            user_id=user_id,
            policy_key="DEL-P1",
            policy_name="테스트 정책",
            estimated_monthly_benefit_krw=100_000,
            linked_at=datetime.now(timezone.utc),
        )
    )
    db_session.commit()

    response = client.request(
        "DELETE",
        "/auth/me",
        json={"password": "secret123"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204

    assert db_session.query(User).filter(User.id == user_id).first() is None
    assert db_session.query(PolicyRecommendation).filter(PolicyRecommendation.user_id == user_id).count() == 0
    assert db_session.query(SavingsLinkedBenefit).filter(SavingsLinkedBenefit.user_id == user_id).count() == 0

    # 탈퇴 후엔 같은 이메일로 다시 로그인할 수 없어야 한다.
    relogin = client.post("/auth/login", json={"email": "delete-me@example.com", "password": "secret123"})
    assert relogin.status_code == 401


def test_signup_stores_extended_profile_fields(client):
    response = client.post(
        "/auth/signup",
        json=_signup_payload(
            "extended@example.com",
            marital_status="newlywed",
            marriage_years=1,
            children_count=0,
            is_pregnant=False,
            desired_region="경기",
            employment_type="regular",
            is_sme_employee=True,
            housing_status="homeless_head",
            net_worth_krw=50_000_000,
            monthly_savings_capacity_krw=1_000_000,
        ),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["marital_status"] == "newlywed"
    assert body["marriage_years"] == 1
    assert body["desired_region"] == "경기"
    assert body["employment_type"] == "regular"
    assert body["is_sme_employee"] is True
    assert body["housing_status"] == "homeless_head"
    assert body["net_worth_krw"] == 50_000_000
    assert body["monthly_savings_capacity_krw"] == 1_000_000
    # marital_status가 있으면 is_married는 marital_status에서 파생된다("newlywed" → True).
    assert body["is_married"] is True


def test_signup_without_extended_fields_defaults_to_null(client):
    response = client.post("/auth/signup", json=_signup_payload("no-extended@example.com"))
    assert response.status_code == 201
    body = response.json()
    assert body["marital_status"] is None
    assert body["net_worth_krw"] is None
    # marital_status가 없으면 기존 is_married 값을 그대로 쓴다(하위 호환).
    assert body["is_married"] is False


def test_signup_marital_status_engaged_keeps_is_married_false(client):
    # "예비부부"는 아직 혼인신고 전이라 정책 매칭 상으로는 미혼과 동일하게 취급한다.
    response = client.post(
        "/auth/signup",
        json=_signup_payload("engaged@example.com", is_married=True, marital_status="engaged"),
    )
    assert response.status_code == 201
    assert response.json()["is_married"] is False


def test_update_profile_sets_extended_fields(client):
    client.post("/auth/signup", json=_signup_payload("extended-update@example.com"))
    login = client.post(
        "/auth/login", json={"email": "extended-update@example.com", "password": "secret123"}
    )
    token = login.json()["access_token"]
    response = client.put(
        "/auth/profile",
        json=_profile_payload(
            marital_status="engaged",
            children_count=1,
            housing_status="homeowner",
        ),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["marital_status"] == "engaged"
    assert body["children_count"] == 1
    assert body["housing_status"] == "homeowner"
    assert body["is_married"] is False


def test_signup_stores_disability_and_veteran_status(client):
    response = client.post(
        "/auth/signup",
        json=_signup_payload("disability-veteran@example.com", has_disability=True, is_veteran=False),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["has_disability"] is True
    assert body["is_veteran"] is False


def test_signup_without_disability_veteran_defaults_to_null(client):
    response = client.post("/auth/signup", json=_signup_payload("no-disability-veteran@example.com"))
    assert response.status_code == 201
    body = response.json()
    assert body["has_disability"] is None
    assert body["is_veteran"] is None


def test_update_profile_sets_disability_and_veteran_status(client):
    client.post("/auth/signup", json=_signup_payload("disability-update@example.com"))
    login = client.post("/auth/login", json={"email": "disability-update@example.com", "password": "secret123"})
    token = login.json()["access_token"]
    response = client.put(
        "/auth/profile",
        json=_profile_payload(has_disability=True, is_veteran=True),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["has_disability"] is True
    assert body["is_veteran"] is True


def test_delete_account_allows_social_only_user_without_password(client, db_session):
    from app.auth.service import get_or_create_social_user
    from app.core.security import create_access_token

    user, _created = get_or_create_social_user(
        db_session, provider="kakao", provider_user_id="social-delete-1", email="social-delete@example.com"
    )
    token = create_access_token(subject=str(user.id))

    response = client.request("DELETE", "/auth/me", json={}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 204


