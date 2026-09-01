"""카카오/네이버 OAuth 2.0 (Authorization Code) 흐름 헬퍼.

브라우저를 프로바이더 인증 페이지로 302 리다이렉트하고(`/auth/{provider}/login`),
프로바이더가 되돌려준 `code`를 백엔드에서 토큰으로 교환한 뒤 사용자 프로필을
가져온다(`/auth/{provider}/callback`). client secret은 서버 밖으로 나가지 않는다.

CSRF 방어용 `state`는 별도 세션 스토어 없이 JWT로 서명해 stateless하게 검증한다
(로그인 시 발급 → 콜백에서 서명·만료·provider 일치 확인).
"""

import time
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
from jose import JWTError, jwt

from app.core.config import settings
from app.core.security import ALGORITHM

KAKAO_AUTHORIZE_URL = "https://kauth.kakao.com/oauth/authorize"
KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
KAKAO_PROFILE_URL = "https://kapi.kakao.com/v2/user/me"

NAVER_AUTHORIZE_URL = "https://nid.naver.com/oauth2.0/authorize"
NAVER_TOKEN_URL = "https://nid.naver.com/oauth2.0/token"
NAVER_PROFILE_URL = "https://openapi.naver.com/v1/nid/me"

SOCIAL_PROVIDERS = ("kakao", "naver")

_STATE_TTL_SECONDS = 600
_HTTP_TIMEOUT = 10.0


class OAuthError(Exception):
    """OAuth 흐름 중 발생한 복구 불가능한 오류 — 라우터는 이걸 잡아 로그인 화면으로 돌려보낸다."""


@dataclass
class SocialProfile:
    provider: str
    provider_user_id: str
    email: str | None
    nickname: str | None


def provider_configured(provider: str) -> bool:
    if provider == "kakao":
        return bool(settings.kakao_client_id)
    if provider == "naver":
        return bool(settings.naver_client_id)
    return False


def _redirect_uri(provider: str) -> str:
    return settings.kakao_redirect_uri if provider == "kakao" else settings.naver_redirect_uri


def issue_state(provider: str) -> str:
    now = int(time.time())
    return jwt.encode(
        {"kind": "oauth_state", "provider": provider, "iat": now, "exp": now + _STATE_TTL_SECONDS},
        settings.jwt_secret,
        algorithm=ALGORITHM,
    )


def verify_state(state: str, provider: str) -> None:
    try:
        payload = jwt.decode(state, settings.jwt_secret, algorithms=[ALGORITHM])
    except JWTError as e:
        raise OAuthError("state 검증 실패 (만료되었거나 위조됨)") from e
    if payload.get("kind") != "oauth_state" or payload.get("provider") != provider:
        raise OAuthError("state가 요청한 provider와 일치하지 않음")


def authorize_url(provider: str, state: str) -> str:
    base = {
        "response_type": "code",
        "redirect_uri": _redirect_uri(provider),
        "state": state,
    }
    if provider == "kakao":
        # 이메일 동의는 비즈앱에서만 필수 지정이 가능하므로 scope는 넘기지 않는다.
        return f"{KAKAO_AUTHORIZE_URL}?{urlencode({**base, 'client_id': settings.kakao_client_id})}"
    if provider == "naver":
        return f"{NAVER_AUTHORIZE_URL}?{urlencode({**base, 'client_id': settings.naver_client_id})}"
    raise OAuthError(f"알 수 없는 provider: {provider}")


def fetch_social_profile(provider: str, code: str, state: str) -> SocialProfile:
    if provider == "kakao":
        return _kakao_profile(code)
    if provider == "naver":
        return _naver_profile(code, state)
    raise OAuthError(f"알 수 없는 provider: {provider}")


def _post_form(url: str, data: dict[str, str | None]) -> dict:
    payload = {k: v for k, v in data.items() if v}
    try:
        with httpx.Client(timeout=_HTTP_TIMEOUT) as client:
            res = client.post(url, data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"})
    except httpx.HTTPError as e:
        raise OAuthError(f"토큰 엔드포인트 호출 실패: {e}") from e
    if res.status_code != 200:
        raise OAuthError(f"토큰 교환 실패 ({res.status_code}): {res.text}")
    return res.json()


def _get_json(url: str, access_token: str) -> dict:
    try:
        with httpx.Client(timeout=_HTTP_TIMEOUT) as client:
            res = client.get(url, headers={"Authorization": f"Bearer {access_token}"})
    except httpx.HTTPError as e:
        raise OAuthError(f"프로필 엔드포인트 호출 실패: {e}") from e
    if res.status_code != 200:
        raise OAuthError(f"프로필 조회 실패 ({res.status_code}): {res.text}")
    return res.json()


def _kakao_profile(code: str) -> SocialProfile:
    token = _post_form(
        KAKAO_TOKEN_URL,
        {
            "grant_type": "authorization_code",
            "client_id": settings.kakao_client_id,
            "client_secret": settings.kakao_client_secret or None,
            "redirect_uri": settings.kakao_redirect_uri,
            "code": code,
        },
    )
    access_token = token.get("access_token")
    if not access_token:
        raise OAuthError("카카오 응답에 access_token 없음")
    data = _get_json(KAKAO_PROFILE_URL, access_token)
    if "id" not in data:
        raise OAuthError("카카오 프로필에 id 없음")
    account = data.get("kakao_account") or {}
    profile = account.get("profile") or {}
    # 이메일은 동의를 받았고(has_email) 검증된(is_email_verified) 경우에만 신뢰한다 —
    # 자동 계정 연동의 판단 근거가 되므로 미검증 이메일은 없는 것으로 취급.
    email = account.get("email")
    if not (account.get("has_email") and account.get("is_email_verified")):
        email = None
    return SocialProfile(
        provider="kakao",
        provider_user_id=str(data["id"]),
        email=email,
        nickname=profile.get("nickname"),
    )


def _naver_profile(code: str, state: str) -> SocialProfile:
    token = _post_form(
        NAVER_TOKEN_URL,
        {
            "grant_type": "authorization_code",
            "client_id": settings.naver_client_id,
            "client_secret": settings.naver_client_secret or None,
            "code": code,
            "state": state,
        },
    )
    access_token = token.get("access_token")
    if not access_token:
        raise OAuthError(f"네이버 응답에 access_token 없음: {token.get('error_description') or token}")
    data = _get_json(NAVER_PROFILE_URL, access_token)
    if data.get("resultcode") != "00":
        raise OAuthError(f"네이버 프로필 조회 실패: {data.get('message')}")
    response = data.get("response") or {}
    if not response.get("id"):
        raise OAuthError("네이버 프로필에 id 없음")
    return SocialProfile(
        provider="naver",
        provider_user_id=str(response["id"]),
        email=response.get("email"),
        nickname=response.get("nickname") or response.get("name"),
    )
