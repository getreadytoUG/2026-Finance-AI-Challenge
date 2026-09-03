from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field, field_validator

from app.auth.service import is_admin_email

# 학생/직장인 등 직업 구분. 프론트 select와 값이 1:1로 맞아야 한다.
OccupationType = Literal["student", "employee", "self_employed", "unemployed", "other"]

# 2026-09-01 UPGRADE.md 반영: 확장 프로필 필드용 타입. 전부 선택 입력(None 허용) —
# 기존 signup/profile 테스트 payload가 이 필드들 없이도 그대로 통과해야 한다.
# 2026-09-03: 미혼/예비부부/신혼부부 3분류 → 미혼/기혼 2분류로 축소(frontend/lib/
# profileOptions.ts와 동일한 변경). "예비신혼부부"는 별도 값 대신 UI 툴팁으로만
# 안내한다. 아래 _normalize_marital_status가 구버전 값(engaged/newlywed)이 기존
# DB 로우나 캐시된 프론트에서 들어와도 깨지지 않게 받아준다.
MaritalStatusType = Literal["single", "married"]
EmploymentType = Literal["regular", "gig_freelance", "business_owner"]
HousingStatusType = Literal["homeless_head", "homeless_member", "homeowner"]

# 2026-09-02 QA에서 발견: 연소득에 999999999999(만원)처럼 비현실적으로 큰 값을 넣으면
# 원 단위로 환산한 값(×10,000)이 users.annual_income_krw(Postgres 32비트 integer,
# 최대 약 21.5억)를 넘겨서 INSERT가 DataError로 죽고, 그 예외가 처리 안 된 채 500이
# 나가면서 CORSMiddleware를 못 거쳐(policy_matcher/router.py의 _raise_as_http_500
# 주석과 동일한 사정) 브라우저에는 원인불명의 "Failed to fetch"만 떴다. 20억원은
# 이 서비스가 다루는 개인 재무 값(연소득/순자산/월저축여력) 어디에도 비현실적이지
# 않을 만큼 넉넉하면서, DB 컬럼 한계보다 충분히 아래라 안전하다.
_MAX_MONEY_KRW = 2_000_000_000
_MAX_AGE = 130


class ExtendedProfileFields(BaseModel):
    marital_status: MaritalStatusType | None = None

    # 2026-09-03: DB에 예전 3분류(engaged/newlywed) 값이 남아있는 로우를 UserOut으로
    # 돌려줄 때도, 캐시된 구버전 프론트가 그 값을 그대로 다시 보낼 때도 이 validator를
    # 거친다 — Literal이 좁아졌다고 기존 유저의 /auth/me가 500이 나면 안 된다.
    @field_validator("marital_status", mode="before")
    @classmethod
    def _normalize_legacy_marital_status(cls, value: str | None) -> str | None:
        if value == "engaged":
            return "single"
        if value == "newlywed":
            return "married"
        return value
    marriage_years: int | None = Field(default=None, ge=0, le=100)
    children_count: int | None = Field(default=None, ge=0, le=20)
    is_pregnant: bool | None = None
    desired_region: str | None = None
    employment_type: EmploymentType | None = None
    is_sme_employee: bool | None = None
    housing_status: HousingStatusType | None = None
    net_worth_krw: int | None = Field(default=None, ge=0, le=_MAX_MONEY_KRW)
    monthly_savings_capacity_krw: int | None = Field(default=None, ge=0, le=_MAX_MONEY_KRW)
    # 2026-09-02 추가: 장애인/국가보훈대상자 전용 정책이 있어 수집(매칭 로직 미반영,
    # 위 확장 필드들과 동일한 사정).
    has_disability: bool | None = None
    is_veteran: bool | None = None


class SignupRequest(ExtendedProfileFields):
    email: EmailStr
    password: str
    age: int = Field(ge=0, le=_MAX_AGE)
    is_married: bool
    annual_income_krw: int = Field(ge=0, le=_MAX_MONEY_KRW)
    region: str
    occupation: OccupationType
    # 배우자 정보는 기혼자도 입력을 생략할 수 있는 선택 항목.
    spouse_age: int | None = Field(default=None, ge=0, le=_MAX_AGE)
    spouse_annual_income_krw: int | None = Field(default=None, ge=0, le=_MAX_MONEY_KRW)
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
    age: int = Field(ge=0, le=_MAX_AGE)
    is_married: bool
    annual_income_krw: int = Field(ge=0, le=_MAX_MONEY_KRW)
    region: str
    occupation: OccupationType
    spouse_age: int | None = Field(default=None, ge=0, le=_MAX_AGE)
    spouse_annual_income_krw: int | None = Field(default=None, ge=0, le=_MAX_MONEY_KRW)
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
