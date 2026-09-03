from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import StaticPool

from app.auth.models import User
from app.core.schema import ensure_schema


def _legacy_users_engine():
    """provider 컬럼이 없던 시절의 users 테이블을 흉내낸 엔진."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE users ("
                " id INTEGER PRIMARY KEY,"
                " email VARCHAR,"
                " hashed_password VARCHAR NOT NULL,"
                " age INTEGER"
                ")"
            )
        )
    return engine


def _columns(engine):
    return {c["name"] for c in inspect(engine).get_columns("users")}


def test_adds_missing_social_columns():
    engine = _legacy_users_engine()
    ensure_schema(engine)
    assert {"provider", "provider_user_id", "name"} <= _columns(engine)


def test_backfills_provider_default_for_existing_rows():
    engine = _legacy_users_engine()
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO users (email, hashed_password) VALUES ('a@b.c', 'x')"))
    ensure_schema(engine)
    with engine.connect() as conn:
        provider = conn.execute(text("SELECT provider FROM users WHERE email='a@b.c'")).scalar_one()
    assert provider == "local"


def test_creates_provider_user_id_index():
    engine = _legacy_users_engine()
    ensure_schema(engine)
    indexes = {ix["name"] for ix in inspect(engine).get_indexes("users")}
    assert "ix_users_provider_user_id" in indexes


def test_is_idempotent():
    engine = _legacy_users_engine()
    ensure_schema(engine)
    ensure_schema(engine)  # 두 번째는 no-op, 에러 없이 지나가야 한다
    assert {"provider", "provider_user_id", "name"} <= _columns(engine)


def test_noop_on_current_schema():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    User.__table__.create(bind=engine)  # 모델대로 만든 최신 테이블
    ensure_schema(engine)  # 손대지 않아야 한다
    assert {"provider", "provider_user_id", "name"} <= _columns(engine)


def test_noop_when_users_table_absent():
    engine = create_engine("sqlite://", poolclass=StaticPool)
    ensure_schema(engine)  # 예외 없이 그냥 리턴


def _legacy_cached_policies_engine():
    """institution_group_code 컬럼이 없던 시절의 users+cached_policies 테이블을 흉내낸 엔진."""
    engine = _legacy_users_engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE cached_policies ("
                " id INTEGER PRIMARY KEY,"
                " policy_key VARCHAR,"
                " region_code VARCHAR"
                ")"
            )
        )
    return engine


def test_adds_institution_group_code_to_cached_policies():
    engine = _legacy_cached_policies_engine()
    ensure_schema(engine)
    columns = {c["name"] for c in inspect(engine).get_columns("cached_policies")}
    assert {"institution_group_code", "school_code", "job_code", "sbiz_code"} <= columns


def test_backfills_institution_group_code_default_for_existing_rows():
    engine = _legacy_cached_policies_engine()
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO cached_policies (policy_key, region_code) VALUES ('P1', '11110')"))
    ensure_schema(engine)
    with engine.connect() as conn:
        value = conn.execute(
            text("SELECT institution_group_code FROM cached_policies WHERE policy_key='P1'")
        ).scalar_one()
    assert value == ""


def test_noop_when_cached_policies_table_absent():
    engine = _legacy_users_engine()  # cached_policies 없이 users만 있는 엔진
    ensure_schema(engine)  # 예외 없이 그냥 넘어가야 한다


def test_adds_extended_profile_columns():
    engine = _legacy_users_engine()
    ensure_schema(engine)
    assert {
        "marital_status",
        "marriage_years",
        "children_count",
        "is_pregnant",
        "desired_region",
        "employment_type",
        "is_sme_employee",
        "housing_status",
        "net_worth_krw",
        "monthly_savings_capacity_krw",
        "has_disability",
        "is_veteran",
    } <= _columns(engine)
