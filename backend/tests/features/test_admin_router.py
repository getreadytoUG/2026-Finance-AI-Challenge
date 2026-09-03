import itertools
from datetime import datetime, timedelta, timezone

from app.auth.service import seed_admin_user
from app.core.config import settings
from app.features.policy_matcher.models import CachedPolicy, PolicyRecommendation

_key_seq = itertools.count(1)


def _signup_login(client, email="normal-user@example.com", **overrides):
    payload = {
        "email": email,
        "password": "secret123",
        "age": 29,
        "is_married": True,
        "annual_income_krw": 40_000_000,
        "region": "서울",
        "occupation": "employee",
    }
    payload.update(overrides)
    client.post("/auth/signup", json=payload)
    login = client.post("/auth/login", json={"email": email, "password": "secret123"})
    return login.json()["access_token"]


def _admin_login(client, db_session):
    seed_admin_user(db_session)
    login = client.post(
        "/auth/login", json={"email": settings.admin_email, "password": settings.admin_password}
    )
    return login.json()["access_token"]


def _seed_policy(db_session, **overrides) -> CachedPolicy:
    defaults = dict(
        policy_key=f"P{next(_key_seq)}",
        policy_name="테스트 정책",
        description="지원 내용",
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


def test_me_reports_is_admin_true_for_admin_account(client, db_session):
    token = _admin_login(client, db_session)
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.json()["is_admin"] is True


def test_me_reports_is_admin_false_for_normal_account(client):
    token = _signup_login(client)
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.json()["is_admin"] is False


def test_admin_endpoints_reject_normal_user(client):
    token = _signup_login(client)
    for method, path in [
        ("get", "/admin/overview"),
        ("get", "/admin/users"),
        ("get", "/admin/users/signup-trend"),
        ("get", "/admin/policies/stats"),
        ("get", "/admin/policies/list"),
        ("get", "/admin/policies/code-values"),
        ("post", "/admin/policies/refresh"),
    ]:
        response = getattr(client, method)(path, headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403, f"{method} {path} should be forbidden for non-admin"


def test_admin_endpoints_reject_unauthenticated(client):
    response = client.get("/admin/overview")
    assert response.status_code == 401


def test_admin_overview_reports_aggregate_counts(client, db_session):
    _signup_login(client, email="u1@example.com", is_married=True)
    _signup_login(client, email="u2@example.com", is_married=False)
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y%m%d")
    _seed_policy(db_session, apply_url="", apply_start_ymd="20200101", apply_end_ymd=yesterday)
    _seed_policy(db_session, apply_url="https://example.com")

    admin_token = _admin_login(client, db_session)
    response = client.get("/admin/overview", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    body = response.json()
    # 관리자 계정 자신도 회원 수에 포함된다.
    assert body["total_users"] == 3
    assert body["married_users"] == 1
    assert body["total_policies"] == 2
    assert body["policies_missing_link"] == 1
    assert body["policies_expired"] == 1


def test_admin_users_lists_all_users(client, db_session):
    _signup_login(client, email="u1@example.com")
    _signup_login(client, email="u2@example.com")
    admin_token = _admin_login(client, db_session)

    response = client.get("/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3  # 일반 유저 2명 + 관리자 자신
    emails = {u["email"] for u in body["users"]}
    assert {"u1@example.com", "u2@example.com", settings.admin_email} == emails
    assert all(u["created_at"] is not None for u in body["users"])


def test_admin_users_reports_null_created_at_for_legacy_rows_without_signup_date(client, db_session):
    from app.auth.models import User

    admin_token = _admin_login(client, db_session)
    db_session.add(
        User(email="legacy@example.com", hashed_password="x", created_at=None)
    )
    db_session.commit()

    response = client.get("/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
    body = response.json()
    legacy = next(u for u in body["users"] if u["email"] == "legacy@example.com")
    assert legacy["created_at"] is None


def test_admin_signup_trend_buckets_signups_by_kst_date(client, db_session):
    from app.auth.models import User

    admin_token = _admin_login(client, db_session)
    today = datetime.now(timezone.utc)
    db_session.add_all(
        [
            User(email="today1@example.com", hashed_password="x", created_at=today),
            User(email="today2@example.com", hashed_password="x", created_at=today),
            User(email="yesterday@example.com", hashed_password="x", created_at=today - timedelta(days=1)),
            User(email="legacy@example.com", hashed_password="x", created_at=None),
        ]
    )
    db_session.commit()

    response = client.get(
        "/admin/users/signup-trend", params={"days": 7}, headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    body = response.json()
    points = {p["date"]: p["count"] for p in body["points"]}
    assert len(points) == 7
    # 관리자 계정 자신도 오늘 가입한 것으로 잡히므로 today는 admin 포함 3명이다.
    kst = timezone(timedelta(hours=9))
    today_key = today.astimezone(kst).date().isoformat()
    assert points[today_key] == 3
    assert body["unknown_signup_date_count"] == 1


def test_admin_signup_trend_defaults_to_last_14_days(client, db_session):
    admin_token = _admin_login(client, db_session)
    response = client.get("/admin/users/signup-trend", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    assert len(response.json()["points"]) == 14


def test_admin_policy_stats_breaks_down_by_category_and_status(client, db_session):
    _seed_policy(db_session, large_category="일자리,주거")
    _seed_policy(db_session, large_category="주거")
    admin_token = _admin_login(client, db_session)

    response = client.get("/admin/policies/stats", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    categories = {c["name"]: c["count"] for c in body["by_category"]}
    assert categories["주거"] == 2
    assert categories["일자리"] == 1
    statuses = {s["status"]: s["count"] for s in body["by_status"]}
    assert statuses["상시"] == 2


def test_admin_policy_list_filters_by_keyword_category_and_status(client, db_session):
    _seed_policy(db_session, policy_name="전세자금 대출", large_category="주거")
    _seed_policy(db_session, policy_name="창업 지원금", large_category="일자리")
    admin_token = _admin_login(client, db_session)

    response = client.get(
        "/admin/policies/list",
        params={"keyword": "전세"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["policy_name"] == "전세자금 대출"

    response = client.get(
        "/admin/policies/list",
        params={"category": "일자리"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["policy_name"] == "창업 지원금"

    response = client.get(
        "/admin/policies/list",
        params={"status": "상시"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.json()["total"] == 2


def test_admin_policy_list_paginates(client, db_session):
    for i in range(25):
        _seed_policy(db_session, policy_name=f"정책{i}")
    admin_token = _admin_login(client, db_session)

    response = client.get(
        "/admin/policies/list",
        params={"page": 2, "page_size": 20},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    body = response.json()
    assert body["total"] == 25
    assert len(body["items"]) == 5
    assert body["page"] == 2


def test_admin_policy_list_includes_description(client, db_session):
    _seed_policy(db_session, policy_name="월세 지원", description="월 20만원씩 최대 12개월 지원")
    admin_token = _admin_login(client, db_session)

    response = client.get("/admin/policies/list", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.json()["items"][0]["description"] == "월 20만원씩 최대 12개월 지원"


def test_admin_policy_list_shows_region_code_as_전국_when_blank(client, db_session):
    _seed_policy(db_session, policy_name="전국 정책", region_code="")
    admin_token = _admin_login(client, db_session)

    response = client.get("/admin/policies/list", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.json()["items"][0]["region_code"] == "전국"


def test_admin_code_values_decodes_marital_status_labels(client, db_session):
    _seed_policy(db_session, marital_status="0055003")
    _seed_policy(db_session, marital_status="0055003")
    _seed_policy(db_session, marital_status="0055001")
    _seed_policy(db_session, marital_status="0055002")
    _seed_policy(db_session, marital_status="9999999")  # 공식 코드표에 없는 미확인 값
    admin_token = _admin_login(client, db_session)

    response = client.get("/admin/policies/code-values", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    body = response.json()
    codes = {c["value"]: c for c in body["marital_status_codes"]}
    assert codes["0055003"]["count"] == 2
    assert codes["0055003"]["label"] == "제한없음"
    assert codes["0055001"]["label"] == "기혼"
    assert codes["0055002"]["label"] == "미혼"
    assert codes["9999999"]["label"] is None


def test_admin_code_values_maps_region_prefixes_and_flags_unknown(client, db_session):
    _seed_policy(db_session, region_code="11110,11140")  # 서울 — 같은 접두사 2번, 정책 1건으로만 카운트
    _seed_policy(db_session, region_code="99999")  # 어떤 REGIONS에도 없는 미확인 접두사
    _seed_policy(db_session, region_code="")  # 전국
    admin_token = _admin_login(client, db_session)

    response = client.get("/admin/policies/code-values", headers={"Authorization": f"Bearer {admin_token}"})
    body = response.json()
    assert body["nationwide_region_count"] == 1
    prefixes = {p["prefix"]: p for p in body["region_prefixes"]}
    assert prefixes["11"]["count"] == 1
    assert prefixes["11"]["mapped_region_names"] == ["서울"]
    assert prefixes["99"]["count"] == 1
    assert prefixes["99"]["mapped_region_names"] == []


def test_admin_code_values_flags_unknown_category_tags(client, db_session):
    _seed_policy(db_session, large_category="일자리,어떤새로운대분류")
    admin_token = _admin_login(client, db_session)

    response = client.get("/admin/policies/code-values", headers={"Authorization": f"Bearer {admin_token}"})
    tags = {t["value"]: t for t in response.json()["large_category_tags"]}
    assert tags["일자리"]["is_known"] is True
    assert tags["어떤새로운대분류"]["is_known"] is False


def test_admin_code_values_reports_last_cache_refresh_time(client, db_session):
    _seed_policy(db_session)
    admin_token = _admin_login(client, db_session)

    response = client.get("/admin/policies/code-values", headers={"Authorization": f"Bearer {admin_token}"})
    body = response.json()
    assert body["cache_last_refreshed_at"] is not None
    assert body["total_policies"] == 1


def test_admin_policy_refresh_triggers_cache_refresh(client, db_session, monkeypatch):
    from app.features.admin import router as admin_router

    monkeypatch.setattr(admin_router, "refresh_policy_cache", lambda db: 42)
    admin_token = _admin_login(client, db_session)

    response = client.post("/admin/policies/refresh", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    assert response.json()["upserted"] == 42


def test_admin_overview_counts_recommendations(client, db_session):
    from app.auth.models import User

    admin_token = _admin_login(client, db_session)
    owner = db_session.query(User).filter(User.email == settings.admin_email).first()
    db_session.add(
        PolicyRecommendation(
            user_id=owner.id,
            policy_key="P1",
            policy_name="정책",
            benefit_description="설명",
            application_period="상시",
            reference_url="https://example.com",
            matched_at=datetime.now(timezone.utc),
            is_read=False,
        )
    )
    db_session.commit()

    response = client.get("/admin/overview", headers={"Authorization": f"Bearer {admin_token}"})
    body = response.json()
    assert body["total_recommendations"] == 1
    assert body["unread_recommendations"] == 1
