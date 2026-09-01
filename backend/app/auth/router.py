from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.auth import oauth, service
from app.auth.models import User
from app.auth.schemas import (
    AccountDeleteRequest,
    EmailAvailabilityOut,
    LoginRequest,
    ProfileUpdateRequest,
    SignupRequest,
    TokenResponse,
    UserOut,
)
from app.core.config import settings
from app.core.db import get_db
from app.core.security import create_access_token, decode_access_token, verify_password

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
            marital_status=payload.marital_status,
            marriage_years=payload.marriage_years,
            children_count=payload.children_count,
            is_pregnant=payload.is_pregnant,
            desired_region=payload.desired_region,
            employment_type=payload.employment_type,
            is_sme_employee=payload.is_sme_employee,
            housing_status=payload.housing_status,
            net_worth_krw=payload.net_worth_krw,
            monthly_savings_capacity_krw=payload.monthly_savings_capacity_krw,
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
    current_user.is_married = service.derive_is_married(payload.marital_status, payload.is_married)
    current_user.annual_income_krw = payload.annual_income_krw
    current_user.region = payload.region
    current_user.occupation = payload.occupation
    current_user.spouse_age = payload.spouse_age
    current_user.spouse_annual_income_krw = payload.spouse_annual_income_krw
    current_user.spouse_occupation = payload.spouse_occupation
    current_user.marital_status = payload.marital_status
    current_user.marriage_years = payload.marriage_years
    current_user.children_count = payload.children_count
    current_user.is_pregnant = payload.is_pregnant
    current_user.desired_region = payload.desired_region
    current_user.employment_type = payload.employment_type
    current_user.is_sme_employee = payload.is_sme_employee
    current_user.housing_status = payload.housing_status
    current_user.net_worth_krw = payload.net_worth_krw
    current_user.monthly_savings_capacity_krw = payload.monthly_savings_capacity_krw
    db.commit()
    db.refresh(current_user)
    return current_user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    payload: AccountDeleteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 로컬(이메일/비밀번호) 계정은 되돌릴 수 없는 작업이라 비밀번호 재확인을 요구한다.
    # 소셜 전용 계정(hashed_password 없음)은 확인할 비밀번호가 없으므로 건너뛴다 —
    # 유효한 JWT 자체가 이미 본인 확인이다.
    # 401이 아니라 403을 쓴다 — 프론트 authedFetch()가 401을 "세션 만료"로 해석해
    # 토큰을 지우고 강제 로그아웃시키는데, 비밀번호를 잘못 입력한 것뿐인 상황에서
    # 그 동작은 원치 않는다(사용자가 다시 시도할 수 있어야 한다).
    if current_user.hashed_password is not None:
        if not payload.password or not verify_password(payload.password, current_user.hashed_password):
            raise HTTPException(status_code=403, detail="비밀번호가 일치하지 않습니다.")
    service.delete_user(db, current_user)
