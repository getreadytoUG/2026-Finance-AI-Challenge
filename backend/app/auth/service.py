from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.auth.models import User
from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.features.policy_matcher.models import PolicyRecommendation
from app.features.savings_planner.models import SavingsLinkedBenefit


def derive_is_married(marital_status: str | None, explicit_is_married: bool | None) -> bool | None:
    # marital_status(미혼/예비부부/신혼부부)가 주어지면 그걸 우선한다 — "예비부부"는
    # 아직 혼인신고 전이라 정책 매칭 로직(is_married 기준) 상으로는 미혼과 동일하게
    # 취급해야 한다. marital_status가 없으면(구버전 클라이언트, 관리자 등) 기존처럼
    # is_married 값을 그대로 쓴다.
    if marital_status is not None:
        return marital_status == "newlywed"
    return explicit_is_married


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
    marital_status: str | None = None,
    marriage_years: int | None = None,
    children_count: int | None = None,
    is_pregnant: bool | None = None,
    desired_region: str | None = None,
    employment_type: str | None = None,
    is_sme_employee: bool | None = None,
    housing_status: str | None = None,
    net_worth_krw: int | None = None,
    monthly_savings_capacity_krw: int | None = None,
    has_disability: bool | None = None,
    is_veteran: bool | None = None,
) -> User:
    existing = db.query(User).filter(User.email == email).first()
    if existing is not None:
        raise ValueError("Email already registered")
    user = User(
        email=email,
        hashed_password=hash_password(password),
        age=age,
        is_married=derive_is_married(marital_status, is_married),
        annual_income_krw=annual_income_krw,
        region=region,
        occupation=occupation,
        spouse_age=spouse_age,
        spouse_annual_income_krw=spouse_annual_income_krw,
        spouse_occupation=spouse_occupation,
        marital_status=marital_status,
        marriage_years=marriage_years,
        children_count=children_count,
        is_pregnant=is_pregnant,
        desired_region=desired_region,
        employment_type=employment_type,
        is_sme_employee=is_sme_employee,
        housing_status=housing_status,
        net_worth_krw=net_worth_krw,
        monthly_savings_capacity_krw=monthly_savings_capacity_krw,
        has_disability=has_disability,
        is_veteran=is_veteran,
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


def _backfill_if_empty(user: User, *, name: str | None, age: int | None) -> bool:
    # 소셜에서 받은 이름/나이는 사용자가 직접 입력한 값이 없을 때만 채운다
    # (기존 프로필 데이터를 덮어쓰지 않는다).
    changed = False
    if name and not user.name:
        user.name = name
        changed = True
    if age is not None and user.age is None:
        user.age = age
        changed = True
    return changed


def get_or_create_social_user(
    db: Session,
    *,
    provider: str,
    provider_user_id: str,
    email: str | None,
    name: str | None = None,
    age: int | None = None,
) -> tuple[User, bool]:
    """소셜 로그인 사용자를 조회하거나 생성한다. ``(user, created)`` 반환.

    우선순위:
      1. ``(provider, provider_user_id)`` 로 기존 소셜 계정을 찾으면 그대로 사용.
      2. 검증된 ``email`` 이 있고 같은 이메일의 기존 계정이 있으면 그 계정에
         이 provider를 붙여 **자동 연동**한다.
      3. 둘 다 아니면 비밀번호 없는 새 계정을 만든다.

    ``name``(프로바이더 닉네임)/``age``(네이버 출생연도 기반)는 빈 필드에만 채운다.
    """
    existing = (
        db.query(User)
        .filter(User.provider == provider, User.provider_user_id == provider_user_id)
        .first()
    )
    if existing is not None:
        if _backfill_if_empty(existing, name=name, age=age):
            db.commit()
            db.refresh(existing)
        return existing, False

    if email:
        by_email = db.query(User).filter(User.email == email).first()
        if by_email is not None:
            by_email.provider = provider
            by_email.provider_user_id = provider_user_id
            _backfill_if_empty(by_email, name=name, age=age)
            db.commit()
            db.refresh(by_email)
            return by_email, False

    user = User(
        email=email or _placeholder_social_email(provider, provider_user_id),
        hashed_password=None,
        provider=provider,
        provider_user_id=provider_user_id,
        name=name,
        age=age,
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user, True


def delete_user(db: Session, user: User) -> None:
    # 이 코드베이스는 ORM relationship/cascade를 쓰지 않고 전부 명시적 쿼리로
    # 처리한다(모델 파일 어디에도 relationship() 호출이 없음) — 그래서 회원탈퇴 시
    # user_id로 이 유저를 참조하는 다른 feature의 테이블도 여기서 직접 지워야 한다.
    # 새 per-user 테이블이 생기면 이 목록도 같이 갱신해야 한다.
    db.query(PolicyRecommendation).filter(PolicyRecommendation.user_id == user.id).delete()
    db.query(SavingsLinkedBenefit).filter(SavingsLinkedBenefit.user_id == user.id).delete()
    db.delete(user)
    db.commit()


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
