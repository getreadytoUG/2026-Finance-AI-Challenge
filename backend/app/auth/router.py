from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.auth import oauth, service
from app.auth.models import User
from app.auth.schemas import (
    EmailAvailabilityOut,
    LoginRequest,
    ProfileUpdateRequest,
    SignupRequest,
    TokenResponse,
    UserOut,
)
from app.core.config import settings
from app.core.db import get_db
from app.core.security import create_access_token, decode_access_token

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


@router.get("/check-email", response_model=EmailAvailabilityOut)
def check_email(email: str, db: Session = Depends(get_db)):
    return EmailAvailabilityOut(available=not service.email_exists(db, email))


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    try:
        user = service.create_user(
            db,
            payload.email,
            payload.password,
            age=payload.age,
            is_married=payload.is_married,
            annual_income_krw=payload.annual_income_krw,
            region=payload.region,
            occupation=payload.occupation,
            spouse_age=payload.spouse_age,
            spouse_annual_income_krw=payload.spouse_annual_income_krw,
            spouse_occupation=payload.spouse_occupation,
        )
    except ValueError as e:
        print(f"[ERROR] /auth/signup failed for email={payload.email!r}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = service.authenticate_user(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(subject=str(user.id))
    return TokenResponse(access_token=token)


@router.get("/{provider}/login")
def social_login(provider: str):
    """브라우저를 프로바이더 인증 페이지로 302 리다이렉트한다."""
    if provider not in oauth.SOCIAL_PROVIDERS:
        raise HTTPException(status_code=404, detail="지원하지 않는 로그인 방식입니다.")
    if not oauth.provider_configured(provider):
        raise HTTPException(status_code=503, detail=f"{provider} 로그인이 설정되지 않았습니다.")
    state = oauth.issue_state(provider)
    return RedirectResponse(oauth.authorize_url(provider, state), status_code=302)


@router.get("/{provider}/callback")
def social_callback(
    provider: str,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    """프로바이더가 되돌려준 code를 토큰으로 교환하고, 유저를 조회/생성한 뒤
    JWT를 URL fragment에 실어 프론트엔드로 리다이렉트한다.

    fragment(`#`)를 쓰는 이유: 쿼리스트링과 달리 서버 접근 로그·Referer 헤더에
    토큰이 남지 않는다."""
    frontend = settings.frontend_base_url.rstrip("/")
    if provider not in oauth.SOCIAL_PROVIDERS:
        raise HTTPException(status_code=404, detail="지원하지 않는 로그인 방식입니다.")
    if error or not code or not state:
        return RedirectResponse(f"{frontend}/login?error=oauth", status_code=302)
    try:
        oauth.verify_state(state, provider)
        social = oauth.fetch_social_profile(provider, code, state)
    except oauth.OAuthError as e:
        print(f"[ERROR] /auth/{provider}/callback failed: {e}")
        return RedirectResponse(f"{frontend}/login?error=oauth", status_code=302)

    user, created = service.get_or_create_social_user(
        db,
        provider=provider,
        provider_user_id=social.provider_user_id,
        email=social.email,
        name=social.nickname,
        age=social.age,
    )
    token = create_access_token(subject=str(user.id))
    fragment = urlencode({"token": token, "new": "1" if created else "0"})
    return RedirectResponse(f"{frontend}/auth/callback#{fragment}", status_code=302)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    if token is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        user_id = decode_access_token(token)
        user = db.query(User).filter(User.id == int(user_id)).first()
    except (JWTError, ValueError) as e:
        print(f"[ERROR] get_current_user failed to decode token: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not service.is_admin_email(current_user.email):
        raise HTTPException(status_code=403, detail="관리자만 접근할 수 있습니다.")
    return current_user


@router.put("/profile", response_model=UserOut)
def update_profile(
    payload: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.age = payload.age
    current_user.is_married = payload.is_married
    current_user.annual_income_krw = payload.annual_income_krw
    current_user.region = payload.region
    current_user.occupation = payload.occupation
    current_user.spouse_age = payload.spouse_age
    current_user.spouse_annual_income_krw = payload.spouse_annual_income_krw
    current_user.spouse_occupation = payload.spouse_occupation
    db.commit()
    db.refresh(current_user)
    return current_user
