from urllib.parse import parse_qs, urlsplit

import pytest

from app.auth import oauth
from app.auth.oauth import SocialProfile


@pytest.fixture()
def kakao_configured(monkeypatch):
    monkeypatch.setattr(oauth.settings, "kakao_client_id", "test-kakao-id")
    monkeypatch.setattr(oauth.settings, "kakao_client_secret", "")


def _fake_profile(**overrides):
    base = dict(provider="kakao", provider_user_id="kakao-1", email="social@example.com", nickname="소셜유저")
    base.update(overrides)
    return lambda provider, code, state: SocialProfile(**base)


def _local_signup(client, email: str) -> dict:
    payload = {
        "email": email,
        "password": "secret123",
        "age": 29,
        "is_married": False,
        "annual_income_krw": 40_000_000,
        "region": "서울",
        "occupation": "employee",
    }
    res = client.post("/auth/signup", json=payload)
    assert res.status_code == 201
    return res.json()


def _callback(client, monkeypatch, *, profile_fn, provider="kakao"):
    monkeypatch.setattr(oauth, "fetch_social_profile", profile_fn)
    state = oauth.issue_state(provider)
    res = client.get(
        f"/auth/{provider}/callback", params={"code": "auth-code", "state": state}, follow_redirects=False
    )
    assert res.status_code == 302
    return res.headers["location"]


def _token_from_fragment(location: str) -> str:
    fragment = urlsplit(location).fragment
    return parse_qs(fragment)["token"][0]


def test_social_login_redirects_to_provider(client, kakao_configured):
    res = client.get("/auth/kakao/login", follow_redirects=False)
    assert res.status_code == 302
    location = res.headers["location"]
    assert location.startswith("https://kauth.kakao.com/oauth/authorize")
    query = parse_qs(urlsplit(location).query)
    assert query["client_id"] == ["test-kakao-id"]
    assert query["response_type"] == ["code"]
    assert query["state"]  # CSRF state present


def test_social_login_unconfigured_returns_503(client, monkeypatch):
    # 개발용 .env에 실제 키가 들어있을 수 있으므로 명시적으로 비운다.
    monkeypatch.setattr(oauth.settings, "kakao_client_id", "")
    res = client.get("/auth/kakao/login", follow_redirects=False)
    assert res.status_code == 503


def test_social_login_unknown_provider_returns_404(client):
    res = client.get("/auth/google/login", follow_redirects=False)
    assert res.status_code == 404


def test_callback_creates_new_social_user(client, monkeypatch):
    location = _callback(client, monkeypatch, profile_fn=_fake_profile(email="new@example.com"))
    assert location.startswith("http://localhost:3000/auth/callback#")
    assert parse_qs(urlsplit(location).fragment)["new"] == ["1"]

    token = _token_from_fragment(location)
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == "new@example.com"
    assert body["provider"] == "kakao"
    assert body["profile_complete"] is False


def test_callback_links_to_existing_local_account_by_email(client, monkeypatch, db_session):
    from app.auth.models import User

    local = _local_signup(client, "dup@example.com")
    location = _callback(client, monkeypatch, profile_fn=_fake_profile(email="dup@example.com"))
    assert parse_qs(urlsplit(location).fragment)["new"] == ["0"]

    token = _token_from_fragment(location)
    body = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert body["id"] == local["id"]  # 같은 계정에 연동됨
    assert body["provider"] == "kakao"
    assert body["profile_complete"] is True  # 기존 로컬 프로필 유지

    assert db_session.query(User).filter(User.email == "dup@example.com").count() == 1


def test_callback_same_social_id_returns_same_user(client, monkeypatch, db_session):
    from app.auth.models import User

    first = _callback(client, monkeypatch, profile_fn=_fake_profile(email="stable@example.com"))
    second = _callback(client, monkeypatch, profile_fn=_fake_profile(email="stable@example.com"))
    assert parse_qs(urlsplit(second).fragment)["new"] == ["0"]

    id_first = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {_token_from_fragment(first)}"}
    ).json()["id"]
    id_second = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {_token_from_fragment(second)}"}
    ).json()["id"]
    assert id_first == id_second
    assert db_session.query(User).count() == 1


def test_password_login_rejected_for_social_only_account(client, monkeypatch):
    _callback(client, monkeypatch, profile_fn=_fake_profile(email="nopass@example.com"))
    res = client.post("/auth/login", json={"email": "nopass@example.com", "password": "anything"})
    assert res.status_code == 401


def test_callback_without_email_uses_placeholder(client, monkeypatch):
    location = _callback(
        client, monkeypatch, profile_fn=_fake_profile(email=None, provider_user_id="kakao-99")
    )
    token = _token_from_fragment(location)
    body = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert body["email"] == "kakao_kakao-99@social.trinity.local"
    assert body["provider"] == "kakao"


def test_callback_stores_social_nickname_as_name(client, monkeypatch):
    location = _callback(
        client, monkeypatch, profile_fn=_fake_profile(email="named@example.com", nickname="희건")
    )
    token = _token_from_fragment(location)
    body = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert body["name"] == "희건"


def test_link_fills_empty_name_but_keeps_existing_profile(client, monkeypatch, db_session):
    _local_signup(client, "keep@example.com")  # age=29, name=None
    location = _callback(
        client,
        monkeypatch,
        profile_fn=_fake_profile(
            provider_user_id="kakao-9", email="keep@example.com", nickname="다른이름"
        ),
    )
    token = _token_from_fragment(location)
    body = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert body["age"] == 29  # 기존 프로필 값 그대로 유지
    assert body["name"] == "다른이름"  # 비어있던 name은 소셜 닉네임으로 채움


def test_callback_with_provider_error_redirects_to_login(client):
    res = client.get(
        "/auth/kakao/callback", params={"error": "access_denied"}, follow_redirects=False
    )
    assert res.status_code == 302
    assert res.headers["location"] == "http://localhost:3000/login?error=oauth"


def test_callback_with_invalid_state_redirects_to_login(client, monkeypatch):
    monkeypatch.setattr(oauth, "fetch_social_profile", _fake_profile())
    res = client.get(
        "/auth/kakao/callback", params={"code": "auth-code", "state": "forged-state"}, follow_redirects=False
    )
    assert res.status_code == 302
    assert res.headers["location"] == "http://localhost:3000/login?error=oauth"


def test_callback_state_for_other_provider_is_rejected(client, monkeypatch):
    monkeypatch.setattr(oauth, "fetch_social_profile", _fake_profile())
    other_state = oauth.issue_state("google")
    res = client.get(
        "/auth/kakao/callback", params={"code": "auth-code", "state": other_state}, follow_redirects=False
    )
    assert res.status_code == 302
    assert res.headers["location"] == "http://localhost:3000/login?error=oauth"
