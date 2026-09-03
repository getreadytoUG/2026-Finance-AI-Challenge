from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.models import User
from app.core.db import Base
from app.core.security import hash_password
from app.features.policy_matcher import recommender
from app.features.policy_matcher.models import CachedPolicy, PolicyRecommendation


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _make_user(db_session, **overrides) -> User:
    defaults = dict(
        email="user@example.com",
        hashed_password=hash_password("secret123"),
        age=29,
        is_married=False,
        annual_income_krw=40_000_000,
        region="서울",
    )
    defaults.update(overrides)
    user = User(**defaults)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _seed_policy(db_session, **overrides) -> CachedPolicy:
    defaults = dict(
        policy_key="P001",
        policy_name="테스트 정책",
        description="지원 내용 설명",
        apply_url="https://www.youthcenter.go.kr",
        application_period="상시",
        apply_start_ymd=None,
        apply_end_ymd=None,
        min_age=19,
        max_age=39,
        min_income_krw=None,
        max_income_krw=None,
        marital_status="",
        region_code="",
        large_category="기타",
        mid_category="",
        refreshed_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    row = CachedPolicy(**defaults)
    db_session.add(row)
    db_session.commit()
    return row


def test_run_recommendation_batch_for_user_skips_incomplete_profile(db_session):
    user = _make_user(db_session, email="a@example.com", age=None)
    _seed_policy(db_session)
    created = recommender.run_recommendation_batch_for_user(db_session, user)
    assert created == 0
    assert db_session.query(PolicyRecommendation).count() == 0


def test_run_recommendation_batch_for_user_saves_eligible_policy(db_session):
    user = _make_user(db_session, email="b@example.com")
    _seed_policy(db_session, policy_key="P001")
    created = recommender.run_recommendation_batch_for_user(db_session, user)
    assert created == 1
    saved = db_session.query(PolicyRecommendation).one()
    assert saved.policy_key == "P001"
    assert saved.user_id == user.id


def test_run_recommendation_batch_for_user_skips_ineligible_policy(db_session):
    user = _make_user(db_session, email="c@example.com")
    # "0055001" = 온통청년 공식 mrgSttsCd 기혼 코드(matching.MARITAL_STATUS_LABELS).
    _seed_policy(db_session, policy_key="P002", marital_status="0055001")
    created = recommender.run_recommendation_batch_for_user(db_session, user)
    assert created == 0


def test_run_recommendation_batch_for_user_skips_policy_without_specific_age_or_income_condition(db_session):
    # 나이/소득 조건이 전혀 없는 정책(온통청년 API의 "0/0" sentinel이 여기서는
    # None으로 정규화된 상태)은 "맞춤" 추천으로서 의미가 없어 알림에서 제외한다.
    user = _make_user(db_session, email="no-condition@example.com")
    _seed_policy(db_session, policy_key="P900", min_age=None, max_age=None, min_income_krw=None, max_income_krw=None)
    created = recommender.run_recommendation_batch_for_user(db_session, user)
    assert created == 0


def test_run_recommendation_batch_for_user_keeps_policy_with_only_income_condition(db_session):
    user = _make_user(db_session, email="income-only@example.com")
    _seed_policy(db_session, policy_key="P901", min_age=None, max_age=None, max_income_krw=60_000_000)
    created = recommender.run_recommendation_batch_for_user(db_session, user)
    assert created == 1


def test_run_recommendation_batch_for_user_skips_policy_with_template_region_code(db_session):
    # 나이 조건은 있어도(has_specific_eligibility_condition 통과), region_code가
    # 17개 시도 중 15개 이상을 커버하는 "복붙 템플릿" 패턴이면 실제로는 특정
    # 지역(예: 울산) 전용인데 지역 필드만 전국형으로 잘못 찍힌 레코드일 가능성이
    # 높다 — 사용자의 지역(서울)과 우연히 겹치더라도 제외해야 한다.
    fifteen_provinces = ",".join(
        f"{p}110"
        for p in ("11", "26", "27", "28", "29", "30", "31", "36", "41", "51", "43", "44", "52", "46", "47")
    )
    user = _make_user(db_session, email="template-region@example.com", region="서울")
    _seed_policy(db_session, policy_key="P903", region_code=fifteen_provinces)
    created = recommender.run_recommendation_batch_for_user(db_session, user)
    assert created == 0


def test_run_recommendation_batch_for_user_keeps_policy_with_genuinely_narrow_region(db_session):
    user = _make_user(db_session, email="narrow-region@example.com", region="서울")
    _seed_policy(db_session, policy_key="P904", region_code="11110,11140")
    created = recommender.run_recommendation_batch_for_user(db_session, user)
    assert created == 1


def test_run_recommendation_batch_for_user_uses_combined_household_income(db_session):
    user = _make_user(
        db_session,
        email="household@example.com",
        is_married=True,
        annual_income_krw=40_000_000,
        spouse_annual_income_krw=20_000_000,
    )
    _seed_policy(db_session, policy_key="P902", max_income_krw=50_000_000)
    created = recommender.run_recommendation_batch_for_user(db_session, user)
    assert created == 0


def test_run_recommendation_batch_for_user_does_not_duplicate_on_second_run(db_session):
    user = _make_user(db_session, email="d@example.com")
    _seed_policy(db_session, policy_key="P003")
    first = recommender.run_recommendation_batch_for_user(db_session, user)
    second = recommender.run_recommendation_batch_for_user(db_session, user)
    assert first == 1
    assert second == 0
    assert db_session.query(PolicyRecommendation).count() == 1


def test_run_recommendation_batch_for_all_users_skips_users_with_incomplete_profile(db_session):
    _make_user(db_session, email="f@example.com", age=None)
    complete_user = _make_user(db_session, email="g@example.com")
    _seed_policy(db_session, policy_key="P004")
    total = recommender.run_recommendation_batch_for_all_users(db_session)
    assert total == 1
    saved = db_session.query(PolicyRecommendation).one()
    assert saved.user_id == complete_user.id


def test_run_recommendation_batch_for_all_users_continues_after_one_user_errors(db_session, monkeypatch):
    _make_user(db_session, email="h@example.com")
    _make_user(db_session, email="i@example.com")
    _seed_policy(db_session, policy_key="P005")

    calls = []
    original_is_eligible = recommender.is_eligible

    def flaky_is_eligible(policy, match_input):
        calls.append(None)
        if len(calls) == 1:
            raise RuntimeError("boom")
        return original_is_eligible(policy, match_input)

    monkeypatch.setattr(recommender, "is_eligible", flaky_is_eligible)
    total = recommender.run_recommendation_batch_for_all_users(db_session)
    assert len(calls) == 2
    assert total == 1
    assert db_session.query(PolicyRecommendation).count() == 1


def test_register_daily_recommendation_job_adds_job_to_scheduler():
    recommender.register_daily_recommendation_job()
    job_ids = {job.id for job in recommender.scheduler.get_jobs()}
    assert "daily_policy_recommendation" in job_ids
