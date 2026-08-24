# 정책 읽기 탭 + 추천 알림 배지 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 온통청년 정책 전체를 카테고리별로 조건 없이 훑어볼 수 있는 "정책 읽기" 탭과, 새로 매칭된 추천 정책에 대한 미확인 배지를 추가한다.

**Architecture:** 온통청년 API 전체 조회 결과를 `cached_policies` 테이블에 캐싱(기존 새벽 3시 배치에 편승)하고, 이 캐시를 카테고리 필터 + 페이지네이션 + 신청상태 배지로 서빙하는 신규 엔드포인트 2개를 추가한다. 추천 목록에는 `is_read` 컬럼과 미확인 개수를 추가해 nav 탭에 배지로 노출한다.

**Tech Stack:** FastAPI + SQLAlchemy(backend), Next.js App Router(frontend) — 기존 스택 그대로.

**Spec:** `docs/superpowers/specs/2026-08-24-policy-browse-notifications-design.md`

## Global Constraints

- 기존 `RawYouthPolicy`를 쓰는 `matching.py`/`tool.py`/`recommender.py`를 깨지 않는다 — 새 필드는 전부 기본값을 준다.
- 새 배치 스케줄을 추가하지 않는다 — 기존 새벽 3시 잡(`_run_daily_recommendation_job`) 안에서 캐시 갱신을 먼저 실행하도록 확장한다.
- 신규 엔드포인트도 기존 `policy_matcher` 라우터와 동일하게 `get_current_user`로 보호한다.
- 마감(🔴)된 정책은 `/browse`와 `/categories` 기본 응답에서 제외한다(`include_closed=true`일 때만 포함).
- 온통청년 API를 직접 건드리는 부분은 mock 테스트만으로 끝내지 말고, 가능하면 실제 키로 라이브 검증한다.

---

### Task 1: `RawYouthPolicy` 확장 + `fetch_all_policies()`

**Files:**
- Modify: `backend/app/features/policy_matcher/youth_center_client.py`
- Test: `backend/tests/features/test_youth_center_client.py`

**Interfaces:**
- Produces: `RawYouthPolicy`에 `large_category: str = ""`, `mid_category: str = ""`, `apply_start_ymd: str | None = None`, `apply_end_ymd: str | None = None` 4개 필드 추가(전부 기본값 있음 — 기존 생성 코드/테스트를 깨지 않음). `fetch_all_policies() -> list[RawYouthPolicy]` 신규 함수.
- Consumes: 없음 (이 파일이 최하위 레이어).

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/features/test_youth_center_client.py`의 `SAMPLE_PAYLOAD`에 아래 필드를 각 정책 항목에 추가한다 (기존 항목들 옆에 이어붙이는 형태):

```python
SAMPLE_PAYLOAD = {
    "resultCode": 200,
    "resultMessage": "성공적으로 데이터를 가지고 왔습니다.",
    "result": {
        "pagging": {"totCount": 2, "pageNum": 1, "pageSize": 100},
        "youthPolicyList": [
            {
                "plcyNo": "P202601",
                "plcyNm": "청년 월세 지원",
                "plcyExplnCn": "월 20만원씩 최대 12개월 지원",
                "aplyUrlAddr": "https://example.com/apply/1",
                "aplyYmd": "20260101 ~ 20261231",
                "sprtTrgtMinAge": "19",
                "sprtTrgtMaxAge": "34",
                "earnMinAmt": "0",
                "earnMaxAmt": "26000000",
                "mrgSttsCd": "",
                "zipCd": "11110,11140",
                "lclsfNm": "주거",
                "mclsfNm": "전월세 및 주거급여 지원",
                "bizPrdBgngYmd": "20260101",
                "bizPrdEndYmd": "20261231",
            },
            {
                "plcyNo": "",
                "plcyNm": "신혼부부 전세임대주택",
                "plcyExplnCn": "시세 대비 저렴한 전세임대",
                "aplyUrlAddr": "https://example.com/apply/2",
                "aplyYmd": "",
                "sprtTrgtMinAge": "0",
                "sprtTrgtMaxAge": "0",
                "earnMinAmt": "0",
                "earnMaxAmt": "0",
                "mrgSttsCd": "기혼",
                "zipCd": "",
                "lclsfNm": "주거",
                "mclsfNm": "임대주택",
                "bizPrdBgngYmd": "        ",
                "bizPrdEndYmd": "        ",
            },
        ],
    },
}
```

파일 맨 아래에 새 테스트를 추가한다:

```python
def test_parse_youth_policy_json_parses_category_and_period_fields():
    policies = _parse_youth_policy_json(SAMPLE_PAYLOAD)
    first = policies[0]
    assert first.large_category == "주거"
    assert first.mid_category == "전월세 및 주거급여 지원"
    assert first.apply_start_ymd == "20260101"
    assert first.apply_end_ymd == "20261231"


def test_parse_youth_policy_json_treats_blank_period_as_none():
    policies = _parse_youth_policy_json(SAMPLE_PAYLOAD)
    second = policies[1]
    assert second.apply_start_ymd is None
    assert second.apply_end_ymd is None


def test_fetch_all_policies_requests_a_large_page_size(monkeypatch):
    from app.features.policy_matcher import youth_center_client

    monkeypatch.setattr(youth_center_client.settings, "youth_center_api_key", "test-key")

    captured = {}

    def fake_get(url, params, timeout):
        captured["params"] = params
        return httpx.Response(
            status_code=200, json=SAMPLE_PAYLOAD, request=httpx.Request("GET", url)
        )

    monkeypatch.setattr(youth_center_client.httpx, "get", fake_get)

    policies = youth_center_client.fetch_all_policies()

    assert captured["params"]["pageSize"] >= 3000
    assert len(policies) == 2
```

- [ ] **Step 2: 테스트 실행해서 실패 확인**

Run: `cd backend && .venv/Scripts/pytest tests/features/test_youth_center_client.py -v`
Expected: 새 3개 테스트가 `AttributeError`(필드 없음) 또는 `AttributeError: module has no attribute 'fetch_all_policies'`로 FAIL.

- [ ] **Step 3: 구현**

`backend/app/features/policy_matcher/youth_center_client.py`의 `RawYouthPolicy`를 아래로 교체:

```python
class RawYouthPolicy(BaseModel):
    policy_id: str
    policy_name: str
    description: str
    apply_url: str
    application_period: str
    min_age: int | None
    max_age: int | None
    min_income_krw: int | None
    max_income_krw: int | None
    marital_status: str
    region_code: str
    large_category: str = ""
    mid_category: str = ""
    apply_start_ymd: str | None = None
    apply_end_ymd: str | None = None
```

`_parse_youth_policy_json`의 `RawYouthPolicy(...)` 생성 부분에 아래 4줄을 추가(기존 필드들 뒤에):

```python
                large_category=item.get("lclsfNm") or "",
                mid_category=item.get("mclsfNm") or "",
                apply_start_ymd=_ymd_or_none(item.get("bizPrdBgngYmd")),
                apply_end_ymd=_ymd_or_none(item.get("bizPrdEndYmd")),
```

파일 끝에 헬퍼와 `fetch_all_policies`를 추가:

```python
def _ymd_or_none(value: str | None) -> str | None:
    # bizPrdBgngYmd/bizPrdEndYmd는 상시/연중 정책이면 공백 8칸("        ")으로 온다.
    if not value:
        return None
    stripped = value.strip()
    return stripped if len(stripped) == 8 and stripped.isdigit() else None


def fetch_all_policies() -> list[RawYouthPolicy]:
    # 실측 결과(2026-08-24) pageSize를 크게 주면 한 번의 요청으로 전체(~2,728건)를
    # 가져올 수 있었다 — 페이지네이션 루프가 필요 없다. totCount가 이 상한을
    # 넘어서면 초과분이 누락되므로 여유 있게 잡는다.
    return fetch_policies(page_num=1, page_size=5000)
```

- [ ] **Step 4: 테스트 실행해서 통과 확인**

Run: `cd backend && .venv/Scripts/pytest tests/features/test_youth_center_client.py -v`
Expected: 전체 PASS.

- [ ] **Step 5: 커밋**

```bash
git add backend/app/features/policy_matcher/youth_center_client.py backend/tests/features/test_youth_center_client.py
git commit -m "feat: parse category/period fields and add fetch_all_policies"
```

---

### Task 2: `CachedPolicy` 모델 + `compute_policy_status` 순수 함수

**Files:**
- Modify: `backend/app/features/policy_matcher/models.py`
- Create: `backend/app/features/policy_matcher/status.py`
- Test: `backend/tests/features/test_status.py`

**Interfaces:**
- Consumes: 없음.
- Produces: `CachedPolicy` SQLAlchemy 모델(Task 3, 4가 사용). `compute_policy_status(apply_start_ymd: str | None, apply_end_ymd: str | None, today: date) -> tuple[str, str]`, `today_kst() -> date` (Task 4가 사용).

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/features/test_status.py` 생성:

```python
from datetime import date

from app.features.policy_matcher.status import compute_policy_status


def test_no_end_date_means_always_open():
    status, emoji = compute_policy_status(None, None, date(2026, 8, 24))
    assert status == "신청가능"
    assert emoji == "🟢"


def test_before_start_date_means_upcoming():
    status, emoji = compute_policy_status("20260901", "20260930", date(2026, 8, 24))
    assert status == "신청예정"
    assert emoji == "⚪"


def test_far_from_deadline_means_open():
    status, emoji = compute_policy_status("20260801", "20260910", date(2026, 8, 24))
    assert status == "신청가능"
    assert emoji == "🟢"


def test_exactly_seven_days_before_deadline_is_closing_soon():
    status, emoji = compute_policy_status("20260801", "20260831", date(2026, 8, 24))
    assert status == "마감임박"
    assert emoji == "🟡"


def test_eight_days_before_deadline_is_still_open():
    status, emoji = compute_policy_status("20260801", "20260901", date(2026, 8, 24))
    assert status == "신청가능"
    assert emoji == "🟢"


def test_after_end_date_means_closed():
    status, emoji = compute_policy_status("20260701", "20260801", date(2026, 8, 24))
    assert status == "마감"
    assert emoji == "🔴"
```

- [ ] **Step 2: 테스트 실행해서 실패 확인**

Run: `cd backend && .venv/Scripts/pytest tests/features/test_status.py -v`
Expected: `ModuleNotFoundError: No module named 'app.features.policy_matcher.status'`로 FAIL.

- [ ] **Step 3: 구현**

`backend/app/features/policy_matcher/status.py` 생성:

```python
from datetime import date, datetime, timedelta, timezone

_KST = timezone(timedelta(hours=9))
_CLOSING_SOON_DAYS = 7


def today_kst() -> date:
    return datetime.now(_KST).date()


def compute_policy_status(
    apply_start_ymd: str | None, apply_end_ymd: str | None, today: date
) -> tuple[str, str]:
    """(상태 텍스트, 이모지) 튜플을 반환한다."""
    if not apply_end_ymd:
        return "신청가능", "🟢"

    end = _parse_ymd(apply_end_ymd)
    if today > end:
        return "마감", "🔴"

    if apply_start_ymd:
        start = _parse_ymd(apply_start_ymd)
        if today < start:
            return "신청예정", "⚪"

    if (end - today).days <= _CLOSING_SOON_DAYS:
        return "마감임박", "🟡"
    return "신청가능", "🟢"


def _parse_ymd(value: str) -> date:
    return date(int(value[0:4]), int(value[4:6]), int(value[6:8]))
```

`backend/app/features/policy_matcher/models.py`에 아래 클래스를 `PolicyRecommendation` 아래에 추가하고, 파일 상단 import에 `Boolean`을 추가한다 (Task 5에서도 `Boolean`을 쓰므로 이번에 같이 추가):

```python
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
```

```python
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
    refreshed_at = Column(DateTime(timezone=True), nullable=False)
```

- [ ] **Step 4: 테스트 실행해서 통과 확인**

Run: `cd backend && .venv/Scripts/pytest tests/features/test_status.py -v`
Expected: 전체 PASS.

- [ ] **Step 5: 커밋**

```bash
git add backend/app/features/policy_matcher/status.py backend/app/features/policy_matcher/models.py backend/tests/features/test_status.py
git commit -m "feat: add CachedPolicy model and policy status calculation"
```

---

### Task 3: 캐시 갱신 배치 (`refresh_policy_cache`) + 스케줄러/시작 시점 연결

**Files:**
- Create: `backend/app/features/policy_matcher/cache.py`
- Modify: `backend/app/features/policy_matcher/recommender.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/features/test_cache.py`

**Interfaces:**
- Consumes: `fetch_all_policies()`(Task 1), `CachedPolicy`(Task 2).
- Produces: `refresh_policy_cache(db: Session) -> int`(upsert된 건수 반환), `seed_policy_cache_if_empty(db: Session) -> None`. Task 4가 `CachedPolicy` 조회로 이 데이터를 소비한다.

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/features/test_cache.py` 생성:

```python
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
```

- [ ] **Step 2: 테스트 실행해서 실패 확인**

Run: `cd backend && .venv/Scripts/pytest tests/features/test_cache.py -v`
Expected: `ModuleNotFoundError: No module named 'app.features.policy_matcher.cache'`로 FAIL.

- [ ] **Step 3: 구현**

`backend/app/features/policy_matcher/cache.py` 생성:

```python
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.features.policy_matcher.models import CachedPolicy
from app.features.policy_matcher.youth_center_client import fetch_all_policies


def refresh_policy_cache(db: Session) -> int:
    policies = fetch_all_policies()
    now = datetime.now(timezone.utc)

    existing = {row.policy_key: row for row in db.query(CachedPolicy).all()}
    seen_keys: set[str] = set()
    upserted = 0

    for policy in policies:
        policy_key = policy.policy_id or policy.policy_name
        if not policy_key or policy_key in seen_keys:
            continue
        seen_keys.add(policy_key)

        row = existing.get(policy_key)
        if row is None:
            row = CachedPolicy(policy_key=policy_key)
            db.add(row)

        row.policy_name = policy.policy_name
        row.description = policy.description
        row.apply_url = policy.apply_url
        row.application_period = policy.application_period
        row.apply_start_ymd = policy.apply_start_ymd
        row.apply_end_ymd = policy.apply_end_ymd
        row.large_category = policy.large_category
        row.mid_category = policy.mid_category
        row.min_age = policy.min_age
        row.max_age = policy.max_age
        row.min_income_krw = policy.min_income_krw
        row.max_income_krw = policy.max_income_krw
        row.marital_status = policy.marital_status
        row.region_code = policy.region_code
        row.refreshed_at = now
        upserted += 1

    db.commit()
    return upserted


def seed_policy_cache_if_empty(db: Session) -> None:
    if db.query(CachedPolicy.id).first() is None:
        refresh_policy_cache(db)
```

`backend/app/features/policy_matcher/recommender.py`의 `_run_daily_recommendation_job`을 아래로 교체 (import 한 줄 추가 + 함수 본문에 한 줄 추가):

```python
from app.features.policy_matcher.cache import refresh_policy_cache
```

```python
def _run_daily_recommendation_job() -> None:
    db = SessionLocal()
    try:
        refresh_policy_cache(db)
        run_recommendation_batch_for_all_users(db)
    finally:
        db.close()
```

`backend/app/main.py`를 수정한다. import 추가:

```python
from app.core.db import Base, SessionLocal, engine
from app.features.policy_matcher.cache import seed_policy_cache_if_empty
```

(`from app.core.db import Base, engine`이던 기존 줄을 `SessionLocal`까지 포함하도록 바꾼다.)

`lifespan` 함수를 아래로 교체:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_policy_cache_if_empty(db)
    finally:
        db.close()
    register_daily_recommendation_job()
    scheduler.start()
    yield
    scheduler.shutdown()
```

- [ ] **Step 4: 테스트 실행해서 통과 확인**

Run: `cd backend && .venv/Scripts/pytest -v`
Expected: 전체 PASS (기존 테스트 포함 회귀 없음 확인).

- [ ] **Step 5: 커밋**

```bash
git add backend/app/features/policy_matcher/cache.py backend/app/features/policy_matcher/recommender.py backend/app/main.py backend/tests/features/test_cache.py
git commit -m "feat: refresh policy cache in the daily batch and seed it on startup"
```

---

### Task 4: `/browse`, `/categories` 엔드포인트

**Files:**
- Modify: `backend/app/features/policy_matcher/schemas.py`
- Modify: `backend/app/features/policy_matcher/router.py`
- Modify: `backend/tests/conftest.py`
- Test: `backend/tests/features/test_policy_browse_router.py`

**Interfaces:**
- Consumes: `CachedPolicy`(Task 2), `compute_policy_status`/`today_kst`(Task 2).
- Produces: `GET /policy_matcher/browse`, `GET /policy_matcher/categories` (프론트 Task 7이 소비).

- [ ] **Step 0: `conftest.py`에 `db_session` fixture 추가 (선행 작업)**

지금 `backend/tests/conftest.py`의 `client` fixture는 엔진을 fixture 함수 안에 지역
변수로만 만들어서, 테스트 코드가 `client`가 실제로 쓰는 DB에 직접 데이터를 심을 방법이
없다(`test_recommender.py`처럼 완전히 별도의 in-memory 엔진을 만들면 `client`가 보는
DB와 달라서 안 보인다). `client`의 기존 동작(요청마다 새 세션, 같은 엔진)은 그대로
유지하면서, 테스트가 직접 쓸 수 있는 세션도 같이 노출하도록 `conftest.py`를 아래로
교체한다:

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.core.db import Base, get_db
from app.main import app


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        app.dependency_overrides.clear()


@pytest.fixture()
def client(db_session):
    return TestClient(app)
```

`client`를 쓰는 기존 테스트들은 그대로 통과해야 한다(요청마다 여전히 새 세션을 받는
동일한 override 방식이라 동작 변화 없음). in-memory SQLite + `StaticPool`은 커넥션을
하나만 유지하므로, 이 Step에서 새로 노출된 `db_session`으로 커밋한 데이터를 `client`를
통한 요청도 그대로 읽는다 — 이 사실이 아래 Step 1 테스트들의 전제다.

이 Step이 끝나면 먼저 기존 전체 스위트를 돌려 회귀가 없는지 확인한다:

Run: `cd backend && .venv/Scripts/pytest -v`
Expected: 지금까지 만든 테스트 전부(Task 1~3 포함) PASS — `conftest.py` 변경으로 인한
회귀가 없어야 한다.

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/features/test_policy_browse_router.py` 생성 (아래 테스트들은 Step 0에서
추가한 `db_session` fixture를 `client`와 함께 사용한다):

```python
from datetime import datetime, timedelta, timezone

from app.features.policy_matcher.models import CachedPolicy


def _signup_login(client, email="browse-user@example.com"):
    client.post("/auth/signup", json={"email": email, "password": "secret123"})
    login = client.post("/auth/login", json={"email": email, "password": "secret123"})
    return login.json()["access_token"]


def _seed_cached_policy(db_session, **overrides):
    defaults = dict(
        policy_key="P100",
        policy_name="테스트 정책",
        description="설명",
        apply_url="https://example.com",
        application_period="상시",
        apply_start_ymd=None,
        apply_end_ymd=None,
        large_category="주거",
        mid_category="임대주택",
        marital_status="",
        region_code="",
        refreshed_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    row = CachedPolicy(**defaults)
    db_session.add(row)
    db_session.commit()
    return row


def test_browse_requires_auth(client):
    response = client.get("/policy_matcher/browse")
    assert response.status_code == 401


def test_browse_returns_open_policy_by_default(client, db_session):
    _seed_cached_policy(db_session, policy_key="P1", policy_name="상시 정책")
    token = _signup_login(client)

    response = client.get("/policy_matcher/browse", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["policy_name"] == "상시 정책"
    assert body["items"][0]["status"] == "신청가능"


def test_browse_excludes_closed_policy_by_default(client, db_session):
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y%m%d")
    _seed_cached_policy(
        db_session, policy_key="P2", policy_name="마감된 정책",
        apply_start_ymd="20200101", apply_end_ymd=yesterday,
    )
    token = _signup_login(client)

    response = client.get("/policy_matcher/browse", headers={"Authorization": f"Bearer {token}"})
    assert response.json()["total"] == 0

    response = client.get(
        "/policy_matcher/browse?include_closed=true", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["status"] == "마감"


def test_browse_filters_by_category(client, db_session):
    _seed_cached_policy(db_session, policy_key="P3", policy_name="주거 정책", large_category="주거")
    _seed_cached_policy(db_session, policy_key="P4", policy_name="금융 정책", large_category="금융")
    token = _signup_login(client)

    response = client.get(
        "/policy_matcher/browse?category=금융", headers={"Authorization": f"Bearer {token}"}
    )
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["policy_name"] == "금융 정책"


def test_browse_paginates(client, db_session):
    for i in range(3):
        _seed_cached_policy(db_session, policy_key=f"P{i}", policy_name=f"정책{i}")
    token = _signup_login(client)

    response = client.get(
        "/policy_matcher/browse?page=1&page_size=2", headers={"Authorization": f"Bearer {token}"}
    )
    body = response.json()
    assert len(body["items"]) == 2
    assert body["total"] == 3
    assert body["page"] == 1


def test_categories_excludes_closed_and_returns_counts(client, db_session):
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y%m%d")
    _seed_cached_policy(db_session, policy_key="P5", large_category="주거")
    _seed_cached_policy(db_session, policy_key="P6", large_category="주거")
    _seed_cached_policy(
        db_session, policy_key="P7", large_category="주거",
        apply_start_ymd="20200101", apply_end_ymd=yesterday,
    )
    token = _signup_login(client)

    response = client.get("/policy_matcher/categories", headers={"Authorization": f"Bearer {token}"})
    body = response.json()
    assert body["categories"] == [{"name": "주거", "count": 2}]
```

- [ ] **Step 2: 테스트 실행해서 실패 확인**

Run: `cd backend && .venv/Scripts/pytest tests/features/test_policy_browse_router.py -v`
Expected: 404(엔드포인트 없음)로 FAIL.

- [ ] **Step 3: 구현**

`backend/app/features/policy_matcher/schemas.py` 끝에 추가:

```python
class PolicyBrowseItem(BaseModel):
    policy_name: str
    benefit_description: str
    application_period: str
    reference_url: str
    large_category: str
    status: str
    status_emoji: str


class PolicyBrowseResponse(BaseModel):
    items: list[PolicyBrowseItem]
    total: int
    page: int
    page_size: int


class PolicyCategoryItem(BaseModel):
    name: str
    count: int


class PolicyCategoryListResponse(BaseModel):
    categories: list[PolicyCategoryItem]
```

`backend/app/features/policy_matcher/router.py`의 기존 import 2줄을 아래로 교체한다
(즉 `from app.features.policy_matcher.models import PolicyRecommendation`과
`from app.features.policy_matcher.schemas import RecommendationListResponse, RecommendationOut, RefreshResponse`
두 줄을 지우고 아래 3줄로 바꾼다):

```python
from app.features.policy_matcher.models import CachedPolicy, PolicyRecommendation
from app.features.policy_matcher.schemas import (
    PolicyBrowseItem,
    PolicyBrowseResponse,
    PolicyCategoryItem,
    PolicyCategoryListResponse,
    RecommendationListResponse,
    RecommendationOut,
    RefreshResponse,
)
from app.features.policy_matcher.status import compute_policy_status, today_kst
```

파일 끝(기존 `list_my_recommendations` 아래)에 추가:

```python
@router.get("/browse", response_model=PolicyBrowseResponse)
def browse_policies(
    page: int = 1,
    page_size: int = 20,
    category: str | None = None,
    include_closed: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    today = today_kst()
    query = db.query(CachedPolicy)
    if category:
        query = query.filter(CachedPolicy.large_category == category)

    matched = []
    for row in query.all():
        status, emoji = compute_policy_status(row.apply_start_ymd, row.apply_end_ymd, today)
        if status == "마감" and not include_closed:
            continue
        matched.append((row, status, emoji))

    total = len(matched)
    start = (page - 1) * page_size
    page_rows = matched[start : start + page_size]

    return PolicyBrowseResponse(
        items=[
            PolicyBrowseItem(
                policy_name=row.policy_name,
                benefit_description=row.description,
                application_period=row.application_period,
                reference_url=row.apply_url,
                large_category=row.large_category,
                status=status,
                status_emoji=emoji,
            )
            for row, status, emoji in page_rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/categories", response_model=PolicyCategoryListResponse)
def list_policy_categories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    today = today_kst()
    counts: dict[str, int] = {}
    for row in db.query(CachedPolicy).all():
        status, _ = compute_policy_status(row.apply_start_ymd, row.apply_end_ymd, today)
        if status == "마감":
            continue
        counts[row.large_category] = counts.get(row.large_category, 0) + 1

    categories = [
        PolicyCategoryItem(name=name, count=count)
        for name, count in sorted(counts.items(), key=lambda pair: -pair[1])
    ]
    return PolicyCategoryListResponse(categories=categories)
```

- [ ] **Step 4: 테스트 실행해서 통과 확인**

Run: `cd backend && .venv/Scripts/pytest -v`
Expected: 전체 PASS.

- [ ] **Step 5: 커밋**

```bash
git add backend/app/features/policy_matcher/schemas.py backend/app/features/policy_matcher/router.py backend/tests/features/test_policy_browse_router.py
git commit -m "feat: add /policy_matcher/browse and /policy_matcher/categories endpoints"
```

---

### Task 5: 추천 `is_read` + 미확인 개수 + 읽음 처리 엔드포인트

**Files:**
- Modify: `backend/app/features/policy_matcher/models.py`
- Modify: `backend/app/features/policy_matcher/schemas.py`
- Modify: `backend/app/features/policy_matcher/router.py`
- Modify: `backend/tests/features/test_policy_matcher_router.py`

**Interfaces:**
- Consumes: 없음 (기존 `PolicyRecommendation` 확장).
- Produces: `GET /policy_matcher/recommendations` 응답에 `unread_count` 추가, `PATCH /policy_matcher/recommendations/{id}/read` 신규. 프론트 Task 8이 소비.

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/features/test_policy_matcher_router.py`에 아래 테스트를 추가한다 (기존
`test_list_returns_only_current_users_recommendations` 아래):

```python
def test_list_includes_unread_count(client, monkeypatch):
    monkeypatch.setattr(recommender, "fetch_policies", lambda: [_policy(policy_id="P300")])
    token = _signup_login_with_profile(client)
    client.post("/policy_matcher/recommendations/refresh", headers={"Authorization": f"Bearer {token}"})

    response = client.get("/policy_matcher/recommendations", headers={"Authorization": f"Bearer {token}"})
    assert response.json()["unread_count"] == 1


def test_mark_recommendation_read_updates_is_read(client, monkeypatch):
    monkeypatch.setattr(recommender, "fetch_policies", lambda: [_policy(policy_id="P301")])
    token = _signup_login_with_profile(client)
    client.post("/policy_matcher/recommendations/refresh", headers={"Authorization": f"Bearer {token}"})
    rec_id = client.get(
        "/policy_matcher/recommendations", headers={"Authorization": f"Bearer {token}"}
    ).json()["recommendations"][0]["id"]

    response = client.patch(
        f"/policy_matcher/recommendations/{rec_id}/read", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["is_read"] is True

    listing = client.get("/policy_matcher/recommendations", headers={"Authorization": f"Bearer {token}"})
    assert listing.json()["unread_count"] == 0


def test_mark_recommendation_read_rejects_other_users_recommendation(client, monkeypatch):
    monkeypatch.setattr(recommender, "fetch_policies", lambda: [_policy(policy_id="P302")])
    token_a = _signup_login_with_profile(client, email="read-a@example.com")
    client.post("/policy_matcher/recommendations/refresh", headers={"Authorization": f"Bearer {token_a}"})
    rec_id = client.get(
        "/policy_matcher/recommendations", headers={"Authorization": f"Bearer {token_a}"}
    ).json()["recommendations"][0]["id"]

    token_b = _signup_login_with_profile(client, email="read-b@example.com")
    response = client.patch(
        f"/policy_matcher/recommendations/{rec_id}/read", headers={"Authorization": f"Bearer {token_b}"}
    )
    assert response.status_code == 404
```

`fetch_policies` mock 시그니처가 Task 1에서 인자를 그대로 유지하므로(`page_num`, `page_size`
디폴트) 위처럼 인자 없이 호출하는 람다로 충분하다.

- [ ] **Step 2: 테스트 실행해서 실패 확인**

Run: `cd backend && .venv/Scripts/pytest tests/features/test_policy_matcher_router.py -v`
Expected: `unread_count`/`is_read` 관련 `KeyError` 또는 404(PATCH 라우트 없음)로 FAIL.

- [ ] **Step 3: 구현**

`backend/app/features/policy_matcher/models.py`의 `PolicyRecommendation`에 필드 추가
(`matched_at` 다음 줄):

```python
    is_read = Column(Boolean, nullable=False, default=False)
```

(Task 2에서 이미 `Boolean`을 import했다면 그대로 재사용.)

`backend/app/features/policy_matcher/schemas.py`의 `RecommendationOut`, `RecommendationListResponse`를 교체:

```python
class RecommendationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    policy_name: str
    benefit_description: str
    application_period: str
    reference_url: str
    matched_at: datetime
    is_read: bool


class RecommendationListResponse(BaseModel):
    recommendations: list[RecommendationOut]
    unread_count: int
```

`backend/app/features/policy_matcher/router.py`의 `list_my_recommendations`를 교체:

```python
@router.get("/recommendations", response_model=RecommendationListResponse)
def list_my_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(PolicyRecommendation)
        .filter(PolicyRecommendation.user_id == current_user.id)
        .order_by(PolicyRecommendation.matched_at.desc())
        .all()
    )
    unread_count = sum(1 for row in rows if not row.is_read)
    return RecommendationListResponse(
        recommendations=[RecommendationOut.model_validate(r) for r in rows],
        unread_count=unread_count,
    )


@router.patch("/recommendations/{recommendation_id}/read", response_model=RecommendationOut)
def mark_recommendation_read(
    recommendation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = (
        db.query(PolicyRecommendation)
        .filter(
            PolicyRecommendation.id == recommendation_id,
            PolicyRecommendation.user_id == current_user.id,
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    row.is_read = True
    db.commit()
    db.refresh(row)
    return RecommendationOut.model_validate(row)
```

- [ ] **Step 4: 테스트 실행해서 통과 확인**

Run: `cd backend && .venv/Scripts/pytest -v`
Expected: 전체 PASS.

- [ ] **Step 5: 커밋**

```bash
git add backend/app/features/policy_matcher/models.py backend/app/features/policy_matcher/schemas.py backend/app/features/policy_matcher/router.py backend/tests/features/test_policy_matcher_router.py
git commit -m "feat: track unread recommendations and add mark-as-read endpoint"
```

---

### Task 6: frontend `lib/api.ts` 확장

**Files:**
- Modify: `frontend/lib/api.ts`

**Interfaces:**
- Consumes: Task 4, 5의 백엔드 응답 shape.
- Produces: `browsePolicies`, `getPolicyCategories`, `markRecommendationRead`, 확장된 `Recommendation` 타입. Task 7, 8이 소비.

- [ ] **Step 1: 기존 `Recommendation` 타입/응답 타입을 교체**

```typescript
export type Recommendation = {
  id: number;
  policy_name: string;
  benefit_description: string;
  application_period: string;
  reference_url: string;
  matched_at: string;
  is_read: boolean;
};

type RecommendationListResponse = {
  recommendations: Recommendation[];
  unread_count: number;
};
```

- [ ] **Step 2: 파일 끝에 신규 타입/함수 추가**

```typescript
export async function markRecommendationRead(token: string, id: number): Promise<void> {
  await authedFetch(`/policy_matcher/recommendations/${id}/read`, token, { method: "PATCH" });
}

export type PolicyBrowseItem = {
  policy_name: string;
  benefit_description: string;
  application_period: string;
  reference_url: string;
  large_category: string;
  status: string;
  status_emoji: string;
};

export type PolicyBrowseResponse = {
  items: PolicyBrowseItem[];
  total: number;
  page: number;
  page_size: number;
};

export async function browsePolicies(
  token: string,
  params: { category?: string; page?: number; pageSize?: number }
): Promise<PolicyBrowseResponse> {
  const search = new URLSearchParams();
  if (params.category) search.set("category", params.category);
  if (params.page) search.set("page", String(params.page));
  if (params.pageSize) search.set("page_size", String(params.pageSize));
  const qs = search.toString();
  const res = await authedFetch(`/policy_matcher/browse${qs ? `?${qs}` : ""}`, token);
  return res.json();
}

export type PolicyCategory = { name: string; count: number };

export async function getPolicyCategories(token: string): Promise<{ categories: PolicyCategory[] }> {
  const res = await authedFetch("/policy_matcher/categories", token);
  return res.json();
}
```

- [ ] **Step 3: 타입 체크**

Run: `cd frontend && npm run build`
Expected: 컴파일 에러 없음 (아직 이 함수들을 쓰는 페이지가 없으므로 미사용 export 경고만
있을 수 있는데, TypeScript는 미사용 export에 에러를 내지 않는다 — 통과해야 한다).

- [ ] **Step 4: 커밋**

```bash
git add frontend/lib/api.ts
git commit -m "feat: add browse/categories/mark-read API client functions"
```

---

### Task 7: "정책 읽기" 탭 (신규 페이지 + nav 등록)

**Files:**
- Create: `frontend/app/(app)/browse/page.tsx`
- Modify: `frontend/app/(app)/layout.tsx`

**Interfaces:**
- Consumes: `browsePolicies`, `getPolicyCategories`, `PolicyBrowseItem`, `PolicyCategory` (Task 6).
- Produces: 없음 (leaf 페이지).

- [ ] **Step 1: `layout.tsx`의 `TABS`에 탭 추가**

`frontend/app/(app)/layout.tsx`의 `TABS` 배열에서 `/policy` 다음 순서에 삽입:

```typescript
const TABS = [
  { href: "/policy", label: "정책비교", icon: "🏛️" },
  { href: "/browse", label: "정책 읽기", icon: "📖" },
  { href: "/savings", label: "저축플랜", icon: "💰" },
  { href: "/subscriptions", label: "구독료 리포트", icon: "📺" },
  { href: "/cards", label: "카드소비 리포트", icon: "💳" },
  { href: "/recommendations", label: "추천", icon: "🔔" },
];
```

- [ ] **Step 2: 페이지 구현**

`frontend/app/(app)/browse/page.tsx` 생성:

```tsx
"use client";

import { useEffect, useState } from "react";
import { browsePolicies, getPolicyCategories } from "@/lib/api";
import type { PolicyBrowseItem, PolicyCategory } from "@/lib/api";

const PAGE_SIZE = 20;

export default function BrowsePage() {
  const [categories, setCategories] = useState<PolicyCategory[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [items, setItems] = useState<PolicyBrowseItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("token") ?? "";
    getPolicyCategories(token)
      .then((res) => setCategories(res.categories))
      .catch(() => {});
  }, []);

  useEffect(() => {
    const token = localStorage.getItem("token") ?? "";
    setLoading(true);
    setError(null);
    browsePolicies(token, { category: selectedCategory ?? undefined, page, pageSize: PAGE_SIZE })
      .then((res) => {
        setItems(res.items);
        setTotal(res.total);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "정책을 불러오지 못했습니다."))
      .finally(() => setLoading(false));
  }, [selectedCategory, page]);

  function handleSelectCategory(name: string | null) {
    setSelectedCategory(name);
    setPage(1);
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <>
      <div className="page-header">
        <h1>📖 정책 읽기</h1>
        <p>조건 입력 없이 전체 정책을 카테고리별로 둘러보세요.</p>
      </div>

      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 20 }}>
        <button
          className="btn-ghost"
          onClick={() => handleSelectCategory(null)}
          style={{
            borderRadius: 999,
            background: selectedCategory === null ? "var(--primary-tint)" : undefined,
            color: selectedCategory === null ? "var(--primary)" : undefined,
          }}
        >
          전체
        </button>
        {categories.map((c) => (
          <button
            key={c.name}
            className="btn-ghost"
            onClick={() => handleSelectCategory(c.name)}
            style={{
              borderRadius: 999,
              background: selectedCategory === c.name ? "var(--primary-tint)" : undefined,
              color: selectedCategory === c.name ? "var(--primary)" : undefined,
            }}
          >
            {c.name} ({c.count})
          </button>
        ))}
      </div>

      {error && <p className="error-text">{error}</p>}
      {loading && <p>불러오는 중...</p>}
      {!loading && items.length === 0 && !error && <p className="error-text">해당하는 정책이 없습니다.</p>}

      <div className="result-list">
        {items.map((item, i) => (
          <div key={i} className="result-item">
            <div className="result-item-title">
              {item.status_emoji} {item.policy_name}
            </div>
            <div className="result-item-row">
              <span>분야</span>
              <span>{item.large_category}</span>
            </div>
            <div className="result-item-row">
              <span>상태</span>
              <span>{item.status}</span>
            </div>
            <div className="result-item-row">
              <span>신청 기간</span>
              <span>{item.application_period}</span>
            </div>
            <div style={{ marginTop: 12 }}>
              <a className="link" href={item.reference_url} target="_blank" rel="noreferrer">
                자세히 보기 →
              </a>
            </div>
          </div>
        ))}
      </div>

      {totalPages > 1 && (
        <div style={{ display: "flex", justifyContent: "center", gap: 8, marginTop: 20 }}>
          <button className="btn-ghost" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            이전
          </button>
          <span style={{ alignSelf: "center", fontSize: 13, color: "var(--text-muted)" }}>
            {page} / {totalPages}
          </span>
          <button className="btn-ghost" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
            다음
          </button>
        </div>
      )}
    </>
  );
}
```

- [ ] **Step 3: 빌드 확인**

Run: `cd frontend && npm run build`
Expected: 컴파일 에러 없음, `/browse` 라우트가 빌드 출력에 나타남.

- [ ] **Step 4: 커밋**

```bash
git add frontend/app/\(app\)/browse frontend/app/\(app\)/layout.tsx
git commit -m "feat: add policy browse tab with category filter and pagination"
```

---

### Task 8: 추천 탭 nav 배지 + 개별 읽음 처리

**Files:**
- Modify: `frontend/app/(app)/layout.tsx`
- Modify: `frontend/app/(app)/recommendations/page.tsx`

**Interfaces:**
- Consumes: `getRecommendations`(기존, `unread_count` 포함하도록 Task 5/6에서 이미 확장됨), `markRecommendationRead`(Task 6).
- Produces: 없음 (leaf UI).

- [ ] **Step 1: `layout.tsx`에 미확인 배지 폴링 추가**

`frontend/app/(app)/layout.tsx` import에 추가:

```typescript
import { getRecommendations } from "@/lib/api";
```

`AppLayout` 함수 내부, 기존 `ready` state 아래에 추가:

```typescript
const [unreadCount, setUnreadCount] = useState(0);
```

기존 인증 가드 `useEffect` 아래에 새 `useEffect` 추가:

```typescript
useEffect(() => {
  if (!ready) return;
  const token = localStorage.getItem("token") ?? "";
  function poll() {
    getRecommendations(token)
      .then((res) => setUnreadCount(res.unread_count))
      .catch(() => {});
  }
  poll();
  const interval = setInterval(poll, 60000);
  return () => clearInterval(interval);
}, [ready]);
```

`TABS.map`으로 탭을 렌더링하는 부분에서, `{tab.icon} {tab.label}` 뒤에 배지를 추가:

```tsx
<span>{tab.icon}</span>
{tab.label}
{tab.href === "/recommendations" && unreadCount > 0 && (
  <span
    style={{
      display: "inline-flex",
      alignItems: "center",
      justifyContent: "center",
      minWidth: 16,
      height: 16,
      padding: "0 4px",
      borderRadius: 999,
      background: "var(--danger)",
      color: "#fff",
      fontSize: 10,
      fontWeight: 700,
    }}
  >
    {unreadCount}
  </span>
)}
```

- [ ] **Step 2: `recommendations/page.tsx`에서 클릭 시 읽음 처리**

import에 `markRecommendationRead` 추가:

```typescript
import { getMe, getRecommendations, markRecommendationRead, refreshRecommendations, updateProfile } from "@/lib/api";
```

`handleRefresh` 함수 아래에 새 함수 추가:

```typescript
async function handleItemClick(rec: Recommendation) {
  if (rec.is_read) return;
  const token = localStorage.getItem("token") ?? "";
  try {
    await markRecommendationRead(token, rec.id);
    setRecommendations((prev) => (prev ? prev.map((r) => (r.id === rec.id ? { ...r, is_read: true } : r)) : prev));
  } catch {
    // 읽음 처리 실패는 조용히 무시 — 목록 자체는 이미 정상 표시되어 있다.
  }
}
```

`result-item` 렌더링 부분을 교체 (클릭 핸들러 + 미확인 표시 추가):

```tsx
{recommendations.map((rec) => (
  <div key={rec.id} className="result-item" onClick={() => handleItemClick(rec)} style={{ cursor: "pointer" }}>
    <div className="result-item-title">
      {!rec.is_read && (
        <span
          style={{
            display: "inline-block",
            width: 8,
            height: 8,
            borderRadius: 999,
            background: "var(--danger)",
            marginRight: 8,
          }}
        />
      )}
      {rec.policy_name}
    </div>
    <div className="result-item-row">
      <span>지원 내용</span>
      <span>{rec.benefit_description}</span>
    </div>
    <div className="result-item-row">
      <span>신청 기간</span>
      <span>{rec.application_period}</span>
    </div>
    <div style={{ marginTop: 12 }}>
      <a className="link" href={rec.reference_url} target="_blank" rel="noreferrer">
        자세히 보기 →
      </a>
    </div>
  </div>
))}
```

(`key={i}` → `key={rec.id}`로 바뀐 점 주의 — `id`가 이제 응답에 있으므로 index 대신 실제 id를 쓴다.)

- [ ] **Step 3: 빌드 확인**

Run: `cd frontend && npm run build`
Expected: 컴파일 에러 없음.

- [ ] **Step 4: 커밋**

```bash
git add frontend/app/\(app\)/layout.tsx frontend/app/\(app\)/recommendations/page.tsx
git commit -m "feat: show unread badge on nav and mark recommendations read on click"
```

---

## 최종 검증 (전체 태스크 완료 후)

- [ ] `cd backend && .venv/Scripts/pytest -v` 전체 PASS
- [ ] `cd frontend && npm run build` 클린
- [ ] 로컬에서 실제 서버 띄우고 Playwright(또는 브라우저)로: (1) "정책 읽기" 탭에서 카테고리
      칩 클릭 시 목록이 바뀌는지, (2) 페이지네이션이 동작하는지, (3) 마감된 정책이 기본
      목록에 안 보이는지, (4) 추천 탭에 미확인 배지 숫자가 뜨는지, (5) 추천 항목 클릭 시
      배지가 줄어드는지 직접 확인
- [ ] `md_files/BACKLOG.md`에서 "정책 카테고리", "신청 기간 관리", "지난 정책 제외",
      "정책 알림" 항목을 상태 갱신 (⬜ → ✅ 또는 🔶)
