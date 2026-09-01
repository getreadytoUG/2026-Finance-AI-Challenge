from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, computed_field

from app.auth.service import is_admin_email

# 학생/직장인 등 직업 구분. 프론트 select와 값이 1:1로 맞아야 한다.
OccupationType = Literal["student", "employee", "self_employed", "unemployed", "other"]


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    age: int
    is_married: bool
    annual_income_krw: int
    region: str
    occupation: OccupationType
    # 배우자 정보는 기혼자도 입력을 생략할 수 있는 선택 항목.
    spouse_age: int | None = None
    spouse_annual_income_krw: int | None = None
    spouse_occupation: OccupationType | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class EmailAvailabilityOut(BaseModel):
    available: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProfileUpdateRequest(BaseModel):
    age: int
    is_married: bool
    annual_income_krw: int
    region: str
    occupation: OccupationType
    spouse_age: int | None = None
    spouse_annual_income_krw: int | None = None
    spouse_occupation: OccupationType | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    # EmailStr가 아니라 str — 카카오가 이메일 동의를 안 준 소셜 계정은
    # 합성 자리표시자 주소(...@social.trinity.local)를 갖는데 email-validator가
    # .local 도메인을 거부하기 때문. 입력(SignupRequest/LoginRequest)은 EmailStr 유지.
    email: str
    provider: str = "local"
    # 표시용 이름 (소셜 닉네임). 이메일 가입은 None → 프론트가 이메일 아이디로 폴백.
    name: str | None = None
    age: int | None = None
    is_married: bool | None = None
    annual_income_krw: int | None = None
    region: str | None = None
    occupation: OccupationType | None = None
    spouse_age: int | None = None
    spouse_annual_income_krw: int | None = None
    spouse_occupation: OccupationType | None = None

    # DB 컬럼이 아니라 이메일이 관리자 계정과 일치하는지로만 판단한다 — 스키마
    # 마이그레이션 없이 관리자 여부를 노출하기 위한 계산 필드.
    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_admin(self) -> bool:
        return is_admin_email(self.email)

    # 소셜 로그인 유저는 프로필 필드 없이 생성되므로, 프론트가 이 값으로
    # 온보딩 페이지 강제 여부를 판단한다. 관리자 계정은 프로필이 의미 없어 예외.
    @computed_field  # type: ignore[prop-decorator]
    @property
    def profile_complete(self) -> bool:
        if self.is_admin:
            return True
        return (
            self.age is not None
            and self.is_married is not None
            and self.annual_income_krw is not None
            and self.region is not None
            and self.occupation is not None
        )
