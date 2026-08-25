from sqlalchemy.orm import Session

from app.auth.models import User
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
