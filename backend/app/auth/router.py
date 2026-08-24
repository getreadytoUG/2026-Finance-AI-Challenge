from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.auth import service
from app.auth.models import User
from app.auth.schemas import LoginRequest, ProfileUpdateRequest, SignupRequest, TokenResponse, UserOut
from app.core.db import get_db
from app.core.security import create_access_token, decode_access_token

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    try:
        user = service.create_user(db, payload.email, payload.password)
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
    db.commit()
    db.refresh(current_user)
    return current_user
