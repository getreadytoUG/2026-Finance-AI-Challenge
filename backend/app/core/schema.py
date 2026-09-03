"""가벼운 스타트업 스키마 보정.

이 프로젝트엔 Alembic이 없고 ``Base.metadata.create_all()`` 은 **없는 테이블만**
만들 뿐 기존 테이블에 컬럼을 추가해주지 않는다. 그래서 모델에 컬럼이 늘어날 때마다
운영 DB(Postgres/Supabase)에 수동 ``ALTER TABLE`` 이 필요했고, 그걸 잊고 배포하면
컨테이너가 ``column ... does not exist`` 로 부팅 크래시했다.

``ensure_schema()`` 는 그 갭을 메운다 — ``create_all()`` 직후 호출되어, 필요한
컬럼이 없으면 idempotent하게 ``ALTER TABLE ADD COLUMN`` 한다. 새로 만들어진 DB는
이미 최신 스키마라 아무 일도 하지 않는다. 새 컬럼이 생기면 여기에 한 블록씩 추가.
"""

import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def ensure_schema(engine: Engine) -> None:
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    if "users" not in table_names:
        return  # 완전히 새 DB — create_all()이 최신 스키마로 만든다.

    columns = {col["name"]: col for col in inspector.get_columns("users")}
    is_postgres = engine.dialect.name == "postgresql"
    ddl: list[str] = []

    # --- 소셜 로그인 컬럼 (provider / provider_user_id) ---
    if "provider" not in columns:
        ddl.append("ALTER TABLE users ADD COLUMN provider VARCHAR NOT NULL DEFAULT 'local'")
    if "provider_user_id" not in columns:
        ddl.append("ALTER TABLE users ADD COLUMN provider_user_id VARCHAR")
        ddl.append(
            "CREATE INDEX IF NOT EXISTS ix_users_provider_user_id ON users (provider_user_id)"
        )
    if "name" not in columns:
        ddl.append("ALTER TABLE users ADD COLUMN name VARCHAR")

    # 소셜 전용 계정은 비밀번호가 없다 → hashed_password NOT NULL 해제.
    # SQLite는 컬럼 제약 변경을 지원하지 않지만, 기존 SQLite 파일엔 전부 값이
    # 들어있고 새 파일은 모델대로 nullable하게 생성되므로 Postgres에서만 처리한다.
    hashed_pw = columns.get("hashed_password")
    if is_postgres and hashed_pw is not None and hashed_pw.get("nullable") is False:
        ddl.append("ALTER TABLE users ALTER COLUMN hashed_password DROP NOT NULL")

    # --- 2026-09-01 UPGRADE.md 확장 프로필 필드 ---
    extended_profile_columns = {
        "marital_status": "VARCHAR",
        "marriage_years": "INTEGER",
        "children_count": "INTEGER",
        "is_pregnant": "BOOLEAN",
        "desired_region": "VARCHAR",
        "employment_type": "VARCHAR",
        "is_sme_employee": "BOOLEAN",
        "housing_status": "VARCHAR",
        "net_worth_krw": "INTEGER",
        "monthly_savings_capacity_krw": "INTEGER",
        # --- 2026-09-02 추가 ---
        "has_disability": "BOOLEAN",
        "is_veteran": "BOOLEAN",
    }
    for column, col_type in extended_profile_columns.items():
        if column not in columns:
            ddl.append(f"ALTER TABLE users ADD COLUMN {column} {col_type}")

    # --- 2026-09-03 추가: cached_policies의 신규 코드값 컬럼들 (matching.py의
    # is_likely_template_region_code / is_student_only_policy 주석 참고) ---
    if "cached_policies" in table_names:
        policy_columns = {col["name"] for col in inspector.get_columns("cached_policies")}
        for column in ("institution_group_code", "school_code", "job_code", "sbiz_code"):
            if column not in policy_columns:
                ddl.append(f"ALTER TABLE cached_policies ADD COLUMN {column} VARCHAR NOT NULL DEFAULT ''")

    if not ddl:
        return

    with engine.begin() as conn:
        for statement in ddl:
            conn.execute(text(statement))
    logger.info("ensure_schema applied %d statement(s): %s", len(ddl), ddl)
