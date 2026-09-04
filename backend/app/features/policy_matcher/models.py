from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint

from app.core.db import Base


class PolicyRecommendation(Base):
    __tablename__ = "policy_recommendations"
    __table_args__ = (UniqueConstraint("user_id", "policy_key", name="uq_policy_recommendation_user_policy"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    policy_key = Column(String, nullable=False)
    policy_name = Column(String, nullable=False)
    benefit_description = Column(String, nullable=False)
    application_period = Column(String, nullable=False)
    reference_url = Column(String, nullable=False)
    matched_at = Column(DateTime(timezone=True), nullable=False)
    is_read = Column(Boolean, nullable=False, default=False)


class CachedPolicy(Base):
    __tablename__ = "cached_policies"

    id = Column(Integer, primary_key=True, index=True)
    policy_key = Column(String, nullable=False, unique=True, index=True)
    policy_name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    apply_url = Column(String, nullable=False)
    application_period = Column(String, nullable=False)
    apply_start_ymd = Column(String, nullable=True)
    apply_end_ymd = Column(String, nullable=True)
    large_category = Column(String, nullable=False, index=True)
    mid_category = Column(String, nullable=False)
    min_age = Column(Integer, nullable=True)
    max_age = Column(Integer, nullable=True)
    min_income_krw = Column(Integer, nullable=True)
    max_income_krw = Column(Integer, nullable=True)
    marital_status = Column(String, nullable=False)
    region_code = Column(String, nullable=False)
    # 2026-09-03 추가: 온통청년 pvsnInstGroupCd(제공기관그룹코드) — "0054001"(중앙부처)
    # | "0054002"(지자체). matching.is_likely_template_region_code()가 "지역코드에
    # 17개 시/도가 다 나열된 게 데이터 실수인지, 햇살론유스처럼 진짜 전국 상품이라
    # 그런 건지"를 구분하는 데 쓴다 — 지자체가 이러면 실수, 중앙부처가 이러면 정상.
    # server_default=''로 기존 행은 빈 문자열로 채워지고(= 지자체로 간주, 안전한
    # 쪽), 다음 배치 갱신 때 실제 값으로 덮어써진다(ensure_schema.py 참고).
    institution_group_code = Column(String, nullable=False, server_default="")
    # 2026-09-03 추가: 온통청년 schoolCd(정책학력요건코드) — "대학 재학" 같은 학력
    # 조건이 있는 정책(국가근로장학금 등)을 matching.is_student_only_policy()가
    # 판별하는 데 쓴다. 나머지 신규 컬럼과 동일하게 server_default로 기존 행 안전.
    school_code = Column(String, nullable=False, server_default="")
    # 2026-09-03 추가: 온통청년 jobCd(정책취업요건코드)/sbizCd(정책특화요건코드) —
    # matching.py의 JOB_STATUS_RULES/is_sme_only_policy 주석 참고.
    job_code = Column(String, nullable=False, server_default="")
    sbiz_code = Column(String, nullable=False, server_default="")
    # 2026-09-04 추가: 온통청년 sbmsnDcmntCn(제출서류)/plcyAplyMthdCn(신청방법) —
    # youth_center_client.py의 RawYouthPolicy 주석 참고. 정책별 챗봇/AI 분석
    # 리포트가 "필요서류가 뭐야?" 질문에 진짜 데이터로 답할 수 있게 한다.
    required_documents = Column(String, nullable=False, server_default="")
    application_method = Column(String, nullable=False, server_default="")
    refreshed_at = Column(DateTime(timezone=True), nullable=False)
