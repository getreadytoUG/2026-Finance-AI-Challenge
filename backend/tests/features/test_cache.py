from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import Base
from app.features.policy_matcher import cache
from app.features.policy_matcher.models import CachedPolicy
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


def _policy(**overrides) -> RawYouthPolicy:
    defaults = dict(
        policy_id="P001",
        policy_name="테스트 정책",
        description="설명",
        apply_url="https://example.com",
        application_period="상시",
        min_age=None,
        max_age=None,
        min_income_krw=None,
        max_income_krw=None,
        marital_status="",
        region_code="",
        large_category="주거",
        mid_category="임대주택",
        apply_start_ymd=None,
        apply_end_ymd=None,
    )
    defaults.update(overrides)
    return RawYouthPolicy(**defaults)


def test_refresh_policy_cache_inserts_new_rows(db_session, monkeypatch):
    monkeypatch.setattr(cache, "fetch_all_policies", lambda: [_policy()])
    upserted = cache.refresh_policy_cache(db_session)
    assert upserted == 1
    row = db_session.query(CachedPolicy).one()
    assert row.policy_key == "P001"
    assert row.large_category == "주거"


def test_refresh_policy_cache_stores_institution_group_code(db_session, monkeypatch):
    monkeypatch.setattr(cache, "fetch_all_policies", lambda: [_policy(institution_group_code="0054001")])
    cache.refresh_policy_cache(db_session)
    row = db_session.query(CachedPolicy).one()
    assert row.institution_group_code == "0054001"


def test_refresh_policy_cache_stores_school_code(db_session, monkeypatch):
    monkeypatch.setattr(cache, "fetch_all_policies", lambda: [_policy(school_code="0049005")])
    cache.refresh_policy_cache(db_session)
    row = db_session.query(CachedPolicy).one()
    assert row.school_code == "0049005"


def test_refresh_policy_cache_falls_back_to_policy_name_when_id_blank(db_session, monkeypatch):
    monkeypatch.setattr(cache, "fetch_all_policies", lambda: [_policy(policy_id="", policy_name="이름만 있는 정책")])
    cache.refresh_policy_cache(db_session)
    row = db_session.query(CachedPolicy).one()
    assert row.policy_key == "이름만 있는 정책"


def test_refresh_policy_cache_updates_existing_row_instead_of_duplicating(db_session, monkeypatch):
    monkeypatch.setattr(cache, "fetch_all_policies", lambda: [_policy(policy_name="이름1")])
    cache.refresh_policy_cache(db_session)
    monkeypatch.setattr(cache, "fetch_all_policies", lambda: [_policy(policy_name="이름2")])
    cache.refresh_policy_cache(db_session)

    assert db_session.query(CachedPolicy).count() == 1
    assert db_session.query(CachedPolicy).one().policy_name == "이름2"


def test_seed_policy_cache_if_empty_skips_when_already_populated(db_session, monkeypatch):
    calls = []
    monkeypatch.setattr(cache, "refresh_policy_cache", lambda db: calls.append(1) or 1)
    db_session.add(
        CachedPolicy(
            policy_key="existing",
            policy_name="이미 있음",
            description="",
            apply_url="",
            application_period="상시",
            large_category="주거",
            mid_category="",
            marital_status="",
            region_code="",
            refreshed_at=datetime.now(timezone.utc),
        )
    )
    db_session.commit()

    cache.seed_policy_cache_if_empty(db_session)
    assert calls == []


def test_seed_policy_cache_if_empty_refreshes_when_empty(db_session, monkeypatch):
    calls = []
    monkeypatch.setattr(cache, "refresh_policy_cache", lambda db: calls.append(1) or 1)
    cache.seed_policy_cache_if_empty(db_session)
    assert calls == [1]
