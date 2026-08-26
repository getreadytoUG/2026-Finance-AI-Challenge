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
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = db.query(User).filter(User.email == email).first()
    if user is None or not verify_password(password, user.hashed_password):
        return None
    return user


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
