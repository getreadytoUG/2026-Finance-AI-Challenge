import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.models import User
from app.core.db import Base
from app.core.security import hash_password
from app.features.policy_matcher import recommender
from app.features.policy_matcher.models import PolicyRecommendation
from app.features.policy_matcher.youth_center_client import RawYouthPolicy


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


def _policy(**overrides) -> RawYouthPolicy:
    defaults = dict(
        policy_id="P001",
        policy_name="테스트 정책",
        description="지원 내용 설명",
        apply_url="https://www.youthcenter.go.kr",
        application_period="상시",
        min_age=19,
        max_age=39,
        min_income_krw=None,
        max_income_krw=None,
        marital_status="",
        region_code="",
    )
    defaults.update(overrides)
    return RawYouthPolicy(**defaults)


def test_run_recommendation_batch_for_user_skips_incomplete_profile(db_session, monkeypatch):
    user = _make_user(db_session, email="a@example.com", age=None)
    monkeypatch.setattr(recommender, "fetch_all_policies", lambda: [_policy()])
    created = recommender.run_recommendation_batch_for_user(db_session, user)
    assert created == 0
    assert db_session.query(PolicyRecommendation).count() == 0


def test_run_recommendation_batch_for_user_saves_eligible_policy(db_session, monkeypatch):
    user = _make_user(db_session, email="b@example.com")
    monkeypatch.setattr(recommender, "fetch_all_policies", lambda: [_policy(policy_id="P001")])
    created = recommender.run_recommendation_batch_for_user(db_session, user)
    assert created == 1
    saved = db_session.query(PolicyRecommendation).one()
    assert saved.policy_key == "P001"
    assert saved.user_id == user.id


def test_run_recommendation_batch_for_user_skips_ineligible_policy(db_session, monkeypatch):
    user = _make_user(db_session, email="c@example.com")
    monkeypatch.setattr(
        recommender, "fetch_all_policies", lambda: [_policy(policy_id="P002", marital_status="기혼")]
    )
    created = recommender.run_recommendation_batch_for_user(db_session, user)
    assert created == 0


def test_run_recommendation_batch_for_user_skips_policy_without_specific_age_or_income_condition(
    db_session, monkeypatch
):
    # 나이/소득 조건이 전혀 없는 정책(온통청년 API의 "0/0" sentinel이 여기서는
    # None으로 정규화된 상태)은 "맞춤" 추천으로서 의미가 없어 알림에서 제외한다.
    user = _make_user(db_session, email="no-condition@example.com")
    monkeypatch.setattr(
        recommender,
        "fetch_all_policies",
        lambda: [_policy(policy_id="P900", min_age=None, max_age=None, min_income_krw=None, max_income_krw=None)],
    )
    created = recommender.run_recommendation_batch_for_user(db_session, user)
    assert created == 0


def test_run_recommendation_batch_for_user_keeps_policy_with_only_income_condition(db_session, monkeypatch):
    user = _make_user(db_session, email="income-only@example.com")
    monkeypatch.setattr(
        recommender,
        "fetch_all_policies",
        lambda: [_policy(policy_id="P901", min_age=None, max_age=None, max_income_krw=60_000_000)],
    )
    created = recommender.run_recommendation_batch_for_user(db_session, user)
    assert created == 1


def test_run_recommendation_batch_for_user_uses_combined_household_income(db_session, monkeypatch):
    user = _make_user(
        db_session,
        email="household@example.com",
        is_married=True,
        annual_income_krw=40_000_000,
        spouse_annual_income_krw=20_000_000,
    )
    monkeypatch.setattr(
        recommender,
        "fetch_all_policies",
        lambda: [_policy(policy_id="P902", max_income_krw=50_000_000)],
    )
    created = recommender.run_recommendation_batch_for_user(db_session, user)
    assert created == 0


def test_run_recommendation_batch_for_user_does_not_duplicate_on_second_run(db_session, monkeypatch):
    user = _make_user(db_session, email="d@example.com")
    monkeypatch.setattr(recommender, "fetch_all_policies", lambda: [_policy(policy_id="P003")])
    first = recommender.run_recommendation_batch_for_user(db_session, user)
    second = recommender.run_recommendation_batch_for_user(db_session, user)
    assert first == 1
    assert second == 0
    assert db_session.query(PolicyRecommendation).count() == 1


def test_run_recommendation_batch_for_user_falls_back_to_policy_name_when_id_blank(db_session, monkeypatch):
    user = _make_user(db_session, email="e@example.com")
    monkeypatch.setattr(
        recommender, "fetch_all_policies", lambda: [_policy(policy_id="", policy_name="이름만 있는 정책")]
    )
    created = recommender.run_recommendation_batch_for_user(db_session, user)
    assert created == 1
    saved = db_session.query(PolicyRecommendation).one()
    assert saved.policy_key == "이름만 있는 정책"


def test_run_recommendation_batch_for_all_users_skips_users_with_incomplete_profile(db_session, monkeypatch):
    _make_user(db_session, email="f@example.com", age=None)
    complete_user = _make_user(db_session, email="g@example.com")
    monkeypatch.setattr(recommender, "fetch_all_policies", lambda: [_policy(policy_id="P004")])
    total = recommender.run_recommendation_batch_for_all_users(db_session)
    assert total == 1
    saved = db_session.query(PolicyRecommendation).one()
    assert saved.user_id == complete_user.id


def test_run_recommendation_batch_for_all_users_continues_after_one_user_errors(db_session, monkeypatch):
    _make_user(db_session, email="h@example.com")
    _make_user(db_session, email="i@example.com")

    calls = []

    def flaky_fetch():
        calls.append(None)
        if len(calls) == 1:
            raise RuntimeError("boom")
        return [_policy(policy_id="P005")]

    monkeypatch.setattr(recommender, "fetch_all_policies", flaky_fetch)
    total = recommender.run_recommendation_batch_for_all_users(db_session)
    assert len(calls) == 2
    assert total == 1
    assert db_session.query(PolicyRecommendation).count() == 1


def test_register_daily_recommendation_job_adds_job_to_scheduler():
    recommender.register_daily_recommendation_job()
    job_ids = {job.id for job in recommender.scheduler.get_jobs()}
    assert "daily_policy_recommendation" in job_ids
