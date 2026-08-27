from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.core.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
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
