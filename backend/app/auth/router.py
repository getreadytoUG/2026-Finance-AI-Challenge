from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.auth import service
from app.auth.models import User
from app.auth.schemas import (
    EmailAvailabilityOut,
    LoginRequest,
    ProfileUpdateRequest,
    SignupRequest,
    TokenResponse,
    UserOut,
)
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
