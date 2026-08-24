from datetime import datetime, timedelta, timezone

from app.features.policy_matcher.models import CachedPolicy


def _signup_login(client, email="browse-user@example.com"):
    client.post("/auth/signup", json={"email": email, "password": "secret123"})
    login = client.post("/auth/login", json={"email": email, "password": "secret123"})
    return login.json()["access_token"]


def _seed_cached_policy(db_session, **overrides):
    defaults = dict(
        policy_key="P100",
        policy_name="테스트 정책",
        description="설명",
        apply_url="https://example.com",
        application_period="상시",
        apply_start_ymd=None,
        apply_end_ymd=None,
        large_category="주거",
        mid_category="임대주택",
        marital_status="",
        region_code="",
        refreshed_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    row = CachedPolicy(**defaults)
    db_session.add(row)
    db_session.commit()
    return row


def test_browse_requires_auth(client):
    response = client.get("/policy_matcher/browse")
    assert response.status_code == 401


def test_browse_returns_open_policy_by_default(client, db_session):
    _seed_cached_policy(db_session, policy_key="P1", policy_name="상시 정책")
    token = _signup_login(client)

    response = client.get("/policy_matcher/browse", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["policy_name"] == "상시 정책"
    assert body["items"][0]["status"] == "상시"


def test_browse_excludes_closed_policy_by_default(client, db_session):
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y%m%d")
    _seed_cached_policy(
        db_session, policy_key="P2", policy_name="마감된 정책",
        apply_start_ymd="20200101", apply_end_ymd=yesterday,
    )
    token = _signup_login(client)

    response = client.get("/policy_matcher/browse", headers={"Authorization": f"Bearer {token}"})
    assert response.json()["total"] == 0

    response = client.get(
        "/policy_matcher/browse?include_closed=true", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["status"] == "만료"


def test_browse_filters_by_category(client, db_session):
    _seed_cached_policy(db_session, policy_key="P3", policy_name="주거 정책", large_category="주거")
    _seed_cached_policy(db_session, policy_key="P4", policy_name="금융 정책", large_category="금융")
    token = _signup_login(client)

    response = client.get(
        "/policy_matcher/browse?category=금융", headers={"Authorization": f"Bearer {token}"}
    )
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["policy_name"] == "금융 정책"


def test_browse_paginates(client, db_session):
    for i in range(3):
        _seed_cached_policy(db_session, policy_key=f"P{i}", policy_name=f"정책{i}")
    token = _signup_login(client)

    response = client.get(
        "/policy_matcher/browse?page=1&page_size=2", headers={"Authorization": f"Bearer {token}"}
    )
    body = response.json()
    assert len(body["items"]) == 2
    assert body["total"] == 3
    assert body["page"] == 1


def test_browse_rejects_invalid_page(client, db_session):
    _seed_cached_policy(db_session, policy_key="P8")
    token = _signup_login(client)

    response = client.get(
        "/policy_matcher/browse?page=0", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 422


def test_browse_deduplicates_repeated_tags_and_matches_any_tag_in_multi_tag_category(client, db_session):
    _seed_cached_policy(
        db_session, policy_key="P9", policy_name="반복 태그 정책", large_category="일자리,일자리,일자리"
    )
    _seed_cached_policy(
        db_session, policy_key="P10", policy_name="복합 태그 정책", large_category="일자리,교육"
    )
    token = _signup_login(client)

    response = client.get(
        "/policy_matcher/browse?category=일자리", headers={"Authorization": f"Bearer {token}"}
    )
    body = response.json()
    assert body["total"] == 2
    names = {item["policy_name"] for item in body["items"]}
    assert names == {"반복 태그 정책", "복합 태그 정책"}

    repeated = next(item for item in body["items"] if item["policy_name"] == "반복 태그 정책")
    assert repeated["large_category"] == "일자리"

    combined = next(item for item in body["items"] if item["policy_name"] == "복합 태그 정책")
    assert combined["large_category"] == "일자리, 교육"


def test_browse_treats_blank_category_as_gita_and_excludes_it_from_category_filter(client, db_session):
    _seed_cached_policy(db_session, policy_key="P11", policy_name="분류 없는 정책", large_category="")
    token = _signup_login(client)

    response = client.get("/policy_matcher/browse", headers={"Authorization": f"Bearer {token}"})
    body = response.json()
    assert body["items"][0]["large_category"] == "기타"

    response = client.get(
        "/policy_matcher/browse?category=기타", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.json()["total"] == 0


def test_categories_deduplicates_repeated_tags_and_counts_each_distinct_tag_once_per_policy(client, db_session):
    _seed_cached_policy(db_session, policy_key="P12", large_category="일자리,일자리,일자리")
    _seed_cached_policy(db_session, policy_key="P13", large_category="일자리,교육")
    token = _signup_login(client)

    response = client.get("/policy_matcher/categories", headers={"Authorization": f"Bearer {token}"})
    body = {c["name"]: c["count"] for c in response.json()["categories"]}
    assert body["일자리"] == 2
    assert body["교육"] == 1


def test_browse_sorts_by_status_임박_여유_상시_예정_만료(client, db_session):
    def ymd(days_from_today: int) -> str:
        return (datetime.now(timezone.utc) + timedelta(days=days_from_today)).strftime("%Y%m%d")

    _seed_cached_policy(
        db_session, policy_key="만료", policy_name="만료", apply_start_ymd=ymd(-30), apply_end_ymd=ymd(-1)
    )
    _seed_cached_policy(db_session, policy_key="상시", policy_name="상시")
    _seed_cached_policy(
        db_session, policy_key="여유", policy_name="여유", apply_start_ymd=ymd(-1), apply_end_ymd=ymd(30)
    )
    _seed_cached_policy(
        db_session, policy_key="임박", policy_name="임박", apply_start_ymd=ymd(-1), apply_end_ymd=ymd(3)
    )
    _seed_cached_policy(
        db_session, policy_key="예정", policy_name="예정", apply_start_ymd=ymd(5), apply_end_ymd=ymd(30)
    )
    token = _signup_login(client)

    response = client.get(
        "/policy_matcher/browse?include_closed=true&page_size=10",
        headers={"Authorization": f"Bearer {token}"},
    )
    names = [item["policy_name"] for item in response.json()["items"]]
    assert names == ["임박", "여유", "상시", "예정", "만료"]


def test_categories_excludes_closed_and_returns_counts(client, db_session):
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y%m%d")
    _seed_cached_policy(db_session, policy_key="P5", large_category="주거")
    _seed_cached_policy(db_session, policy_key="P6", large_category="주거")
    _seed_cached_policy(
        db_session, policy_key="P7", large_category="주거",
        apply_start_ymd="20200101", apply_end_ymd=yesterday,
    )
    token = _signup_login(client)

    response = client.get("/policy_matcher/categories", headers={"Authorization": f"Bearer {token}"})
    body = response.json()
    assert body["categories"] == [{"name": "주거", "count": 2}]


def test_categories_includes_closed_when_include_closed_is_true(client, db_session):
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y%m%d")
    _seed_cached_policy(db_session, policy_key="P5", large_category="주거")
    _seed_cached_policy(
        db_session, policy_key="P6", large_category="주거",
        apply_start_ymd="20200101", apply_end_ymd=yesterday,
    )
    token = _signup_login(client)

    response = client.get(
        "/policy_matcher/categories?include_closed=true", headers={"Authorization": f"Bearer {token}"}
    )
    body = response.json()
    assert body["categories"] == [{"name": "주거", "count": 2}]
