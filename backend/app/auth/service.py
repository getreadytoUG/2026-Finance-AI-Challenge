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


# 배포마다 SQLite가 초기화되는 문제 때문에 매번 회원가입부터 다시 해야 하는 게
# 번거로워서 만든 고정 데모 계정. 민감한 실서비스 계정이 아니라 데모 편의용이라
# 자격증명을 그대로 코드에 둔다 — 이미 있으면 아무것도 안 한다(idempotent).
DEMO_USER_EMAIL = "test@naver.com"
DEMO_USER_PASSWORD = "test123!"


def seed_demo_user(db: Session) -> None:
    if db.query(User.id).filter(User.email == DEMO_USER_EMAIL).first() is not None:
        return
    create_user(db, DEMO_USER_EMAIL, DEMO_USER_PASSWORD)
