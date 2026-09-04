from sqlalchemy import Column, DateTime, Integer, String

from app.core.db import Base


class Notice(Base):
    __tablename__ = "notices"

    id = Column(Integer, primary_key=True, index=True)
    # 자유 문자열(정책 대분류처럼 고정 코드표가 아님) — 프론트는 "금리"/"상품"/
    # "정책"/"서비스" 네 가지를 예시로 쓰지만 값 자체를 강제하지 않는다.
    category = Column(String, nullable=False)
    title = Column(String, nullable=False)
    content = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
