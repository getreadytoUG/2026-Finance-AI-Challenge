from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, computed_field

from app.auth.service import is_admin_email

# 학생/직장인 등 직업 구분. 프론트 select와 값이 1:1로 맞아야 한다.
OccupationType = Literal["student", "employee", "self_employed", "unemployed", "other"]

# 2026-09-01 UPGRADE.md 반영: 확장 프로필 필드용 타입. 전부 선택 입력(None 허용) —
# 기존 signup/profile 테스트 payload가 이 필드들 없이도 그대로 통과해야 한다.
MaritalStatusType = Literal["single", "engaged", "newlywed"]
EmploymentType = Literal["regular", "gig_freelance", "business_owner"]
HousingStatusType = Literal["homeless_head", "homeless_member", "homeowner"]


class ExtendedProfileFields(BaseModel):
    marital_status: MaritalStatusType | None = None
    marriage_years: int | None = None
    children_count: int | None = None
    is_pregnant: bool | None = None
    desired_region: str | None = None
    employment_type: EmploymentType | None = None
    is_sme_employee: bool | None = None
    housing_status: HousingStatusType | None = None
    net_worth_krw: int | None = None
    monthly_savings_capacity_krw: int | None = None


class SignupRequest(ExtendedProfileFields):
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


class AccountDeleteRequest(BaseModel):
    # 소셜 전용 계정(hashed_password가 없는)은 확인할 비밀번호가 없으므로 생략 가능 —
    # 이미 유효한 JWT로 인증됐다는 사실 자체가 본인 확인이다. 로컬(이메일/비밀번호)
    # 계정은 router에서 이 값을 필수로 검증한다.
    password: str | None = None


class ProfileUpdateRequest(ExtendedProfileFields):
    age: int
    is_married: bool
    annual_income_krw: int
    region: str
    occupation: OccupationType
    spouse_age: int | None = None
    spouse_annual_income_krw: int | None = None
    spouse_occupation: OccupationType | None = None


class UserOut(ExtendedProfileFields):
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
