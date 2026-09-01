from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.core.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    # 소셜 전용 계정은 비밀번호가 없으므로 nullable. 값이 NULL이면
    # authenticate_user()가 비밀번호 로그인을 거부한다.
    hashed_password = Column(String, nullable=True)
    # "local"(이메일/비밀번호) | "kakao" | "naver".
    provider = Column(String, nullable=False, server_default="local", default="local")
    # 프로바이더가 발급한 그 사용자 고유 ID(문자열). local 계정은 NULL.
    # (provider, provider_user_id) 조합으로 소셜 계정을 식별한다.
    provider_user_id = Column(String, nullable=True, index=True)
    # 표시용 이름. 소셜 로그인 시 프로바이더 닉네임으로 채워진다. 이메일 가입은 NULL
    # → 프론트가 이메일 아이디(앞부분)로 폴백한다.
    name = Column(String, nullable=True)
    age = Column(Integer, nullable=True)
    is_married = Column(Boolean, nullable=True)
    annual_income_krw = Column(Integer, nullable=True)
    region = Column(String, nullable=True)
    occupation = Column(String, nullable=True)
    spouse_age = Column(Integer, nullable=True)
    spouse_annual_income_krw = Column(Integer, nullable=True)
    spouse_occupation = Column(String, nullable=True)
    # nullable인 이유: 이 컬럼 추가 이전에 가입한 기존 유저는 실제 가입 시각을
    # 알 방법이 없다 — Base.metadata.create_all()은 이미 있는 테이블에 컬럼을
    # 추가해주지 않으므로, 운영 DB에는 별도로 ALTER TABLE을 한 번 실행했다
    # (기존 행은 NULL로 남음). 관리자 대시보드의 가입 추이 집계는 이 값이
    # 있는 유저만 대상으로 한다.
    created_at = Column(DateTime(timezone=True), nullable=True)
