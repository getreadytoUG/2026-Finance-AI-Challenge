from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.auth.models import User
from app.core.config import settings
from app.core.security import hash_password, verify_password


def create_user(
    db: Session,
    email: str,
    password: str,
    *,
    age: int | None = None,
    is_married: bool | None = None,
    annual_income_krw: int | None = None,
    region: str | None = None,
    occupation: str | None = None,
    spouse_age: int | None = None,
    spouse_annual_income_krw: int | None = None,
    spouse_occupation: str | None = None,
) -> User:
    existing = db.query(User).filter(User.email == email).first()
    if existing is not None:
        raise ValueError("Email already registered")
    user = User(
        email=email,
        hashed_password=hash_password(password),
        age=age,
        is_married=is_married,
        annual_income_krw=annual_income_krw,
        region=region,
        occupation=occupation,
        spouse_age=spouse_age,
        spouse_annual_income_krw=spouse_annual_income_krw,
        spouse_occupation=spouse_occupation,
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = db.query(User).filter(User.email == email).first()
    # hashed_password가 None이면 소셜 전용 계정 — 비밀번호 로그인 불가.
    if user is None or user.hashed_password is None:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def _placeholder_social_email(provider: str, provider_user_id: str) -> str:
    # 카카오가 이메일 동의를 안 준 경우 email 컬럼(NOT NULL·UNIQUE)을 채우기 위한
    # 자리표시자. 실제 수신 불가 주소이며, 온보딩에서 사용자가 고치도록 유도한다.
    return f"{provider}_{provider_user_id}@social.trinity.local"


def get_or_create_social_user(
    db: Session,
    *,
    provider: str,
    provider_user_id: str,
    email: str | None,
) -> tuple[User, bool]:
    """소셜 로그인 사용자를 조회하거나 생성한다. ``(user, created)`` 반환.

    우선순위:
      1. ``(provider, provider_user_id)`` 로 기존 소셜 계정을 찾으면 그대로 사용.
      2. 검증된 ``email`` 이 있고 같은 이메일의 기존 계정이 있으면 그 계정에
         이 provider를 붙여 **자동 연동**한다.
      3. 둘 다 아니면 비밀번호 없는 새 계정을 만든다.
    """
    existing = (
        db.query(User)
        .filter(User.provider == provider, User.provider_user_id == provider_user_id)
        .first()
    )
    if existing is not None:
        return existing, False

    if email:
        by_email = db.query(User).filter(User.email == email).first()
        if by_email is not None:
            by_email.provider = provider
            by_email.provider_user_id = provider_user_id
            db.commit()
            db.refresh(by_email)
            return by_email, False

    user = User(
        email=email or _placeholder_social_email(provider, provider_user_id),
        hashed_password=None,
        provider=provider,
        provider_user_id=provider_user_id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user, True


def email_exists(db: Session, email: str) -> bool:
    return db.query(User).filter(User.email == email).first() is not None


def is_admin_email(email: str) -> bool:
    return email == settings.admin_email


def seed_admin_user(db: Session) -> None:
    # 프로필 필드(나이/소득/지역 등)는 관리자 계정에 의미가 없어 전부 비워둔다 —
    # is_admin_email()이 이메일만으로 관리자 여부를 판단하므로 프로필은 필요 없다.
    if email_exists(db, settings.admin_email):
        return
    create_user(db, settings.admin_email, settings.admin_password)
