# 정책 자동 추천 (매일 배치 + 앱 내 알림) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 유저가 프로필(나이/혼인여부/소득/지역)을 저장해두면, 매일 온통청년 API를 조회해 새로 맞는 정책이 나왔을 때 앱 내 "추천" 탭에 쌓이도록 한다. 로그인 유저는 하루를 기다리지 않고 본인 계정만 즉시 갱신할 수도 있다.

**Architecture:** `User`에 프로필 필드를 추가하고, `policy_matcher`의 매칭 로직(`_is_eligible`)을 `matching.py`로 공개 함수화해 대화형 조회(`tool.py`)와 배치 엔진(`recommender.py`)이 공유한다. 배치 엔진은 `PolicyRecommendation` 테이블에 결과를 저장하며 `(user_id, policy_key)`로 중복을 막는다. `policy_key`는 새로 추가하는 `RawYouthPolicy.policy_id`(추정 필드, 비어있으면 `policy_name`으로 대체)를 쓴다. 스케줄러(APScheduler)가 백엔드 프로세스 안에서 매일 배치 엔진을 전체 유저 대상으로 실행하고, 별도 REST 엔드포인트가 로그인 유저 본인만 즉시 갱신/조회할 수 있게 한다.

**Tech Stack:** 기존 FastAPI/SQLAlchemy/pytest 스택 + 신규 의존성 `apscheduler`.

**Spec:** [docs/superpowers/specs/2026-08-21-policy-recommendation-batch-design.md](../specs/2026-08-21-policy-recommendation-batch-design.md)

## Global Constraints

- 매칭 조건 판단은 `app/features/policy_matcher/matching.py`의 `is_eligible()` 하나로 통일한다 — `tool.py`와 `recommender.py` 둘 다 이 함수를 재사용하고, 각자 조건 로직을 따로 구현하지 않는다.
- `RawYouthPolicy.policy_id`는 다른 필드들과 마찬가지로 실제 API 응답 필드명이 미검증인 추정치(`plcyNo`)다 — 비어있으면 `policy_name`을 중복 방지용 대체 키로 쓴다.
- 단일 유저 경로(대화형 `/tools/policy_matcher`, 수동 갱신 `/policy_matcher/recommendations/refresh`, 그리고 `run_recommendation_batch_for_user` 자체)는 `fetch_policies` 실패 시 예외를 그대로 던진다. **`run_recommendation_batch_for_all_users`만 예외**: 유저 단위로 캐치·로그하고 다음 유저로 계속 진행한다.
- 프로필 업데이트는 부분 업데이트가 아니라 4개 필드(`age`, `is_married`, `annual_income_krw`, `region`)를 한 번에 채우는 단일 폼 제출이다.
- 스케줄러는 "매일 3시에 실제로 도는지"는 테스트하지 않는다 — 잡이 스케줄러에 등록되는지만 확인한다.
- 추천 목록에는 읽음/안읽음 상태가 없다 — 항상 전체를 최신순으로 보여준다.
- 프로필 입력 폼은 별도 마이페이지가 아니라 새 "추천" 탭 안에 넣는다.

---

## Task 1: 유저 프로필 확장 (`User` 모델 + `PUT /auth/profile`)

**Files:**
- Modify: `backend/app/auth/models.py`
- Modify: `backend/app/auth/schemas.py`
- Modify: `backend/app/auth/router.py`
- Modify: `backend/tests/test_auth.py`

**Interfaces:**
- Produces: `User.age: int | None`, `User.is_married: bool | None`, `User.annual_income_krw: int | None`, `User.region: str | None` — Task 4(recommender)의 `_has_complete_profile()`이 이 4개 필드를 검사
- Produces: `app.auth.schemas.ProfileUpdateRequest(age: int, is_married: bool, annual_income_krw: int, region: str)`
- Produces: `UserOut`에 위 4개 필드 추가(전부 `| None = None`)
- Produces: 라우트 `PUT /auth/profile` (인증 필요, `UserOut` 반환)

- [ ] **Step 1: 실패하는 테스트를 `backend/tests/test_auth.py`에 추가**

기존 파일 끝에 추가:

```python
def test_update_profile_sets_fields_and_returns_them(client):
    client.post("/auth/signup", json={"email": "e@example.com", "password": "secret123"})
    login = client.post("/auth/login", json={"email": "e@example.com", "password": "secret123"})
    token = login.json()["access_token"]
    response = client.put(
        "/auth/profile",
        json={"age": 29, "is_married": False, "annual_income_krw": 40_000_000, "region": "서울"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["age"] == 29
    assert body["is_married"] is False
    assert body["annual_income_krw"] == 40_000_000
    assert body["region"] == "서울"


def test_update_profile_requires_auth(client):
    response = client.put(
        "/auth/profile",
        json={"age": 29, "is_married": False, "annual_income_krw": 40_000_000, "region": "서울"},
    )
    assert response.status_code == 401


def test_me_reflects_profile_after_update(client):
    client.post("/auth/signup", json={"email": "f@example.com", "password": "secret123"})
    login = client.post("/auth/login", json={"email": "f@example.com", "password": "secret123"})
    token = login.json()["access_token"]
    client.put(
        "/auth/profile",
        json={"age": 31, "is_married": True, "annual_income_krw": 55_000_000, "region": "부산"},
        headers={"Authorization": f"Bearer {token}"},
    )
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.json()["region"] == "부산"


def test_me_returns_null_profile_fields_before_update(client):
    client.post("/auth/signup", json={"email": "g@example.com", "password": "secret123"})
    login = client.post("/auth/login", json={"email": "g@example.com", "password": "secret123"})
    token = login.json()["access_token"]
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    body = response.json()
    assert body["age"] is None
    assert body["is_married"] is None
    assert body["annual_income_krw"] is None
    assert body["region"] is None
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run (from `backend/`): `.venv/Scripts/pytest tests/test_auth.py -v`
Expected: FAIL — `404 Not Found` for `PUT /auth/profile` (route doesn't exist yet), `KeyError`/`assert None == ...` for the `/auth/me` field checks

- [ ] **Step 3: `app/auth/models.py`에 컬럼 추가**

```python
from sqlalchemy import Boolean, Column, Integer, String

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
```

- [ ] **Step 4: `app/auth/schemas.py`에 `ProfileUpdateRequest` 추가하고 `UserOut` 확장**

```python
from pydantic import BaseModel, ConfigDict, EmailStr


class SignupRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProfileUpdateRequest(BaseModel):
    age: int
    is_married: bool
    annual_income_krw: int
    region: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    age: int | None = None
    is_married: bool | None = None
    annual_income_krw: int | None = None
    region: str | None = None
```

- [ ] **Step 5: `app/auth/router.py`에 `PUT /profile` 라우트 추가**

`router.py`의 import 목록에 `ProfileUpdateRequest` 추가:

```python
from app.auth.schemas import LoginRequest, ProfileUpdateRequest, SignupRequest, TokenResponse, UserOut
```

`me()` 함수 뒤에 추가:

```python
@router.put("/profile", response_model=UserOut)
def update_profile(
    payload: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.age = payload.age
    current_user.is_married = payload.is_married
    current_user.annual_income_krw = payload.annual_income_krw
    current_user.region = payload.region
    db.commit()
    db.refresh(current_user)
    return current_user
```

- [ ] **Step 6: 테스트 통과 확인**

Run (from `backend/`): `.venv/Scripts/pytest tests/test_auth.py -v`
Expected: PASS (10개 — 기존 6개 + 신규 4개)

- [ ] **Step 7: 전체 백엔드 테스트 실행해 회귀 없는지 확인**

Run (from `backend/`): `.venv/Scripts/pytest -v`
Expected: PASS 전체

- [ ] **Step 8: Commit**

```bash
git add backend/app/auth/models.py backend/app/auth/schemas.py backend/app/auth/router.py backend/tests/test_auth.py
git commit -m "feat: add user profile fields and PUT /auth/profile endpoint"
```

---

## Task 2: `RawYouthPolicy`에 `policy_id` 추가 (중복 추천 방지용 식별자)

**Files:**
- Modify: `backend/app/features/policy_matcher/youth_center_client.py`
- Modify: `backend/tests/features/test_youth_center_client.py`
- Modify: `backend/tests/features/test_policy_matcher.py`
- Modify: `backend/tests/test_tools_router.py`

**Interfaces:**
- Produces: `RawYouthPolicy.policy_id: str` (다른 필드들처럼 필수, 빈 문자열 가능) — Task 4(recommender)가 이 필드를 `policy_name`과 함께 중복 방지 키로 사용

- [ ] **Step 1: `test_youth_center_client.py`의 `SAMPLE_XML`과 관련 assertion을 수정**

`SAMPLE_XML`의 각 `<youthPolicy>` 안, `<plcyNm>` 바로 앞에 `<plcyNo>` 태그 추가:

```python
SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<youthPolicyList>
  <youthPolicy>
    <plcyNo>P202601</plcyNo>
    <plcyNm>청년 월세 지원</plcyNm>
    <plcyExplnCn>월 20만원씩 최대 12개월 지원</plcyExplnCn>
    <aplyUrlAddr>https://example.com/apply/1</aplyUrlAddr>
    <aplyYmd>20260101 ~ 20261231</aplyYmd>
    <sprtTrgtMinAge>19</sprtTrgtMinAge>
    <sprtTrgtMaxAge>34</sprtTrgtMaxAge>
    <earnMinAmt></earnMinAmt>
    <earnMaxAmt>26000000</earnMaxAmt>
    <mrgSttsCd></mrgSttsCd>
    <zipCd>서울</zipCd>
  </youthPolicy>
  <youthPolicy>
    <plcyNo></plcyNo>
    <plcyNm>신혼부부 전세임대주택</plcyNm>
    <plcyExplnCn>시세 대비 저렴한 전세임대</plcyExplnCn>
    <aplyUrlAddr>https://example.com/apply/2</aplyUrlAddr>
    <aplyYmd></aplyYmd>
    <sprtTrgtMinAge></sprtTrgtMinAge>
    <sprtTrgtMaxAge></sprtTrgtMaxAge>
    <earnMinAmt></earnMinAmt>
    <earnMaxAmt></earnMaxAmt>
    <mrgSttsCd>기혼</mrgSttsCd>
    <zipCd></zipCd>
  </youthPolicy>
</youthPolicyList>
"""
```

`test_parse_youth_policy_xml_parses_full_record`에 assertion 추가:

```python
def test_parse_youth_policy_xml_parses_full_record():
    policies = _parse_youth_policy_xml(SAMPLE_XML)
    first = policies[0]
    assert first.policy_id == "P202601"
    assert first.policy_name == "청년 월세 지원"
    assert first.description == "월 20만원씩 최대 12개월 지원"
    assert first.apply_url == "https://example.com/apply/1"
    assert first.application_period == "20260101 ~ 20261231"
    assert first.min_age == 19
    assert first.max_age == 34
    assert first.min_income_krw is None
    assert first.max_income_krw == 26_000_000
    assert first.marital_status == ""
    assert first.region_code == "서울"
```

`test_parse_youth_policy_xml_defaults_missing_fields_to_none_or_empty`에 assertion 추가:

```python
def test_parse_youth_policy_xml_defaults_missing_fields_to_none_or_empty():
    policies = _parse_youth_policy_xml(SAMPLE_XML)
    second = policies[1]
    assert second.policy_id == ""
    assert second.marital_status == "기혼"
    assert second.min_age is None
    assert second.max_age is None
    assert second.application_period == "상시"
    assert second.region_code == ""
```

- [ ] **Step 2: `test_policy_matcher.py`의 `_policy()` 헬퍼에 `policy_id` 기본값 추가**

`_policy()` 함수의 `defaults` dict 첫 줄에 추가:

```python
def _policy(**overrides) -> RawYouthPolicy:
    defaults = dict(
        policy_id="",
        policy_name="테스트 정책",
        description="지원 내용 설명",
        apply_url="https://www.youthcenter.go.kr",
        application_period="상시",
        min_age=None,
        max_age=None,
        min_income_krw=None,
        max_income_krw=None,
        marital_status="",
        region_code="",
    )
    defaults.update(overrides)
    return RawYouthPolicy(**defaults)
```

- [ ] **Step 3: `test_tools_router.py`의 `RawYouthPolicy(...)` 생성부에 `policy_id` 추가**

```python
            RawYouthPolicy(
                policy_id="",
                policy_name="청년 전세자금대출 (테스트)",
                description="전세자금을 지원합니다",
                apply_url="https://www.example.com",
                application_period="상시",
                min_age=None,
                max_age=None,
                min_income_krw=None,
                max_income_krw=None,
                marital_status="",
                region_code="",
            )
```

- [ ] **Step 4: 테스트가 실패하는지 확인**

Run (from `backend/`): `.venv/Scripts/pytest tests/features/test_youth_center_client.py tests/features/test_policy_matcher.py tests/test_tools_router.py -v`
Expected: FAIL — `pydantic.ValidationError` (`policy_id` field required) on every `RawYouthPolicy(...)` construction, plus `AttributeError: 'RawYouthPolicy' object has no attribute 'policy_id'` on the new assertions

- [ ] **Step 5: `youth_center_client.py`에 `policy_id` 필드와 파싱 추가**

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
```

`_parse_youth_policy_xml()`의 `RawYouthPolicy(...)` 생성부 첫 줄에 추가:

```python
            RawYouthPolicy(
                policy_id=_text(item, "plcyNo"),
                policy_name=_text(item, "plcyNm"),
                description=_text(item, "plcyExplnCn"),
                apply_url=_text(item, "aplyUrlAddr"),
                application_period=_text(item, "aplyYmd") or "상시",
                min_age=_int_or_none(_text(item, "sprtTrgtMinAge")),
                max_age=_int_or_none(_text(item, "sprtTrgtMaxAge")),
                min_income_krw=_int_or_none(_text(item, "earnMinAmt")),
                max_income_krw=_int_or_none(_text(item, "earnMaxAmt")),
                marital_status=_text(item, "mrgSttsCd"),
                region_code=_text(item, "zipCd"),
            )
```

(`plcyNo`는 다른 태그명들과 마찬가지로 미검증 추정치다 — 파일 상단의 기존 NOTE 주석이 이미 이 상황을 설명하고 있으므로 추가 주석은 필요 없다.)

- [ ] **Step 6: 테스트 통과 확인**

Run (from `backend/`): `.venv/Scripts/pytest tests/features/test_youth_center_client.py tests/features/test_policy_matcher.py tests/test_tools_router.py -v`
Expected: PASS 전체

- [ ] **Step 7: 전체 백엔드 테스트 실행해 회귀 없는지 확인**

Run (from `backend/`): `.venv/Scripts/pytest -v`
Expected: PASS 전체

- [ ] **Step 8: Commit**

```bash
git add backend/app/features/policy_matcher/youth_center_client.py backend/tests/features/test_youth_center_client.py backend/tests/features/test_policy_matcher.py backend/tests/test_tools_router.py
git commit -m "feat: add policy_id to RawYouthPolicy for dedup keying"
```

---

## Task 3: 매칭 로직을 `matching.py`로 공개 함수화

**Files:**
- Create: `backend/app/features/policy_matcher/matching.py`
- Modify: `backend/app/features/policy_matcher/tool.py`
- Test: `backend/tests/features/test_matching.py`

**Interfaces:**
- Consumes: `RawYouthPolicy`, `PolicyMatchInput` (기존)
- Produces: `app.features.policy_matcher.matching.is_eligible(policy: RawYouthPolicy, input: PolicyMatchInput) -> bool` — Task 5(recommender)가 이 함수를 재사용

- [ ] **Step 1: 실패하는 테스트를 `backend/tests/features/test_matching.py`에 작성**

```python
from app.features.policy_matcher.matching import is_eligible
from app.features.policy_matcher.schemas import PolicyMatchInput
from app.features.policy_matcher.youth_center_client import RawYouthPolicy


def _policy(**overrides) -> RawYouthPolicy:
    defaults = dict(
        policy_id="",
        policy_name="테스트 정책",
        description="지원 내용 설명",
        apply_url="https://www.youthcenter.go.kr",
        application_period="상시",
        min_age=None,
        max_age=None,
        min_income_krw=None,
        max_income_krw=None,
        marital_status="",
        region_code="",
    )
    defaults.update(overrides)
    return RawYouthPolicy(**defaults)


def _input(**overrides) -> PolicyMatchInput:
    defaults = dict(age=29, is_married=False, annual_income_krw=40_000_000, region="서울")
    defaults.update(overrides)
    return PolicyMatchInput(**defaults)


def test_policy_without_conditions_is_always_eligible():
    assert is_eligible(_policy(), _input()) is True


def test_applicant_outside_age_range_is_ineligible():
    assert is_eligible(_policy(min_age=19, max_age=34), _input(age=50)) is False


def test_marriage_requirement_is_enforced_both_ways():
    policy = _policy(marital_status="기혼")
    assert is_eligible(policy, _input(is_married=False)) is False
    assert is_eligible(policy, _input(is_married=True)) is True


def test_income_ceiling_is_enforced():
    assert is_eligible(_policy(max_income_krw=30_000_000), _input(annual_income_krw=40_000_000)) is False


def test_income_floor_is_enforced():
    assert is_eligible(_policy(min_income_krw=50_000_000), _input(annual_income_krw=40_000_000)) is False


def test_region_restricted_policy_is_ineligible_outside_region():
    assert is_eligible(_policy(region_code="부산"), _input(region="서울")) is False


def test_region_restricted_policy_is_ineligible_when_input_region_empty():
    assert is_eligible(_policy(region_code="부산"), _input(region="")) is False
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run (from `backend/`): `.venv/Scripts/pytest tests/features/test_matching.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.features.policy_matcher.matching'`

- [ ] **Step 3: `app/features/policy_matcher/matching.py` 작성**

```python
from app.features.policy_matcher.schemas import PolicyMatchInput
from app.features.policy_matcher.youth_center_client import RawYouthPolicy


def is_eligible(policy: RawYouthPolicy, input: PolicyMatchInput) -> bool:
    if policy.min_age is not None and input.age < policy.min_age:
        return False
    if policy.max_age is not None and input.age > policy.max_age:
        return False
    # marital_status는 youth_center_client._parse_youth_policy_xml()이 "기혼"/"미혼"/""로
    # 정규화한다고 가정한다 — 실제 API 코드 체계 확인 시 그쪽과 함께 맞춰야 한다.
    if policy.marital_status == "기혼" and not input.is_married:
        return False
    if policy.marital_status == "미혼" and input.is_married:
        return False
    if policy.min_income_krw is not None and input.annual_income_krw < policy.min_income_krw:
        return False
    if policy.max_income_krw is not None and input.annual_income_krw > policy.max_income_krw:
        return False
    if policy.region_code and (not input.region or (policy.region_code not in input.region and input.region not in policy.region_code)):
        return False
    return True
```

- [ ] **Step 4: `tool.py`가 `matching.is_eligible`을 쓰도록 수정**

```python
from app.features.policy_matcher.matching import is_eligible
from app.features.policy_matcher.schemas import PolicyMatchInput, PolicyMatchOutput, PolicyOption
from app.features.policy_matcher.youth_center_client import fetch_policies
from app.tools.base import ToolContext, ToolSpec


def run(input: PolicyMatchInput, ctx: ToolContext) -> PolicyMatchOutput:
    policies = fetch_policies(query=input.region)
    options = [
        PolicyOption(
            policy_name=policy.policy_name,
            eligible=is_eligible(policy, input),
            benefit_description=policy.description,
            application_period=policy.application_period,
            reference_url=policy.apply_url,
        )
        for policy in policies
    ]
    return PolicyMatchOutput(options=options)


TOOL_SPEC = ToolSpec(
    name="policy_matcher",
    description="청년/신혼부부 정책을 비교하고 가/불가를 판단합니다",
    input_schema=PolicyMatchInput,
    output_schema=PolicyMatchOutput,
    entrypoint=run,
)
```

(`_is_eligible`과 `RawYouthPolicy` import는 이제 필요 없으므로 제거한다 — `run()`의 동작 자체는 바뀌지 않는다, 로직이 옮겨졌을 뿐이다.)

- [ ] **Step 5: 테스트 통과 확인**

Run (from `backend/`): `.venv/Scripts/pytest tests/features/test_matching.py tests/features/test_policy_matcher.py -v`
Expected: PASS 전체 (`test_policy_matcher.py`는 `run()`을 블랙박스로 테스트하므로 코드 변경 없이 그대로 통과해야 한다)

- [ ] **Step 6: 전체 백엔드 테스트 실행해 회귀 없는지 확인**

Run (from `backend/`): `.venv/Scripts/pytest -v`
Expected: PASS 전체

- [ ] **Step 7: Commit**

```bash
git add backend/app/features/policy_matcher/matching.py backend/app/features/policy_matcher/tool.py backend/tests/features/test_matching.py
git commit -m "refactor: extract policy matching logic into matching.py for reuse"
```

---

## Task 4: 추천 저장 테이블 + 배치 엔진 (`recommender.py`)

**Files:**
- Create: `backend/app/features/policy_matcher/models.py`
- Create: `backend/app/features/policy_matcher/recommender.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/features/test_recommender.py`

**Interfaces:**
- Consumes: `app.auth.models.User` (Task 1의 프로필 필드), `matching.is_eligible` (Task 3), `youth_center_client.fetch_policies`/`RawYouthPolicy` (Task 2)
- Produces: `app.features.policy_matcher.models.PolicyRecommendation(id, user_id, policy_key, policy_name, benefit_description, application_period, reference_url, matched_at)`
- Produces: `app.features.policy_matcher.recommender.run_recommendation_batch_for_user(db: Session, user: User) -> int` — Task 5(router)가 호출
- Produces: `app.features.policy_matcher.recommender.run_recommendation_batch_for_all_users(db: Session) -> int` — Task 6(scheduler)이 호출

- [ ] **Step 1: 실패하는 테스트를 `backend/tests/features/test_recommender.py`에 작성**

```python
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
        min_age=None,
        max_age=None,
        min_income_krw=None,
        max_income_krw=None,
        marital_status="",
        region_code="",
    )
    defaults.update(overrides)
    return RawYouthPolicy(**defaults)


def test_run_recommendation_batch_for_user_skips_incomplete_profile(db_session, monkeypatch):
    user = _make_user(db_session, email="a@example.com", age=None)
    monkeypatch.setattr(recommender, "fetch_policies", lambda query=None: [_policy()])
    created = recommender.run_recommendation_batch_for_user(db_session, user)
    assert created == 0
    assert db_session.query(PolicyRecommendation).count() == 0


def test_run_recommendation_batch_for_user_saves_eligible_policy(db_session, monkeypatch):
    user = _make_user(db_session, email="b@example.com")
    monkeypatch.setattr(recommender, "fetch_policies", lambda query=None: [_policy(policy_id="P001")])
    created = recommender.run_recommendation_batch_for_user(db_session, user)
    assert created == 1
    saved = db_session.query(PolicyRecommendation).one()
    assert saved.policy_key == "P001"
    assert saved.user_id == user.id


def test_run_recommendation_batch_for_user_skips_ineligible_policy(db_session, monkeypatch):
    user = _make_user(db_session, email="c@example.com")
    monkeypatch.setattr(
        recommender, "fetch_policies", lambda query=None: [_policy(policy_id="P002", marital_status="기혼")]
    )
    created = recommender.run_recommendation_batch_for_user(db_session, user)
    assert created == 0


def test_run_recommendation_batch_for_user_does_not_duplicate_on_second_run(db_session, monkeypatch):
    user = _make_user(db_session, email="d@example.com")
    monkeypatch.setattr(recommender, "fetch_policies", lambda query=None: [_policy(policy_id="P003")])
    first = recommender.run_recommendation_batch_for_user(db_session, user)
    second = recommender.run_recommendation_batch_for_user(db_session, user)
    assert first == 1
    assert second == 0
    assert db_session.query(PolicyRecommendation).count() == 1


def test_run_recommendation_batch_for_user_falls_back_to_policy_name_when_id_blank(db_session, monkeypatch):
    user = _make_user(db_session, email="e@example.com")
    monkeypatch.setattr(
        recommender, "fetch_policies", lambda query=None: [_policy(policy_id="", policy_name="이름만 있는 정책")]
    )
    created = recommender.run_recommendation_batch_for_user(db_session, user)
    assert created == 1
    saved = db_session.query(PolicyRecommendation).one()
    assert saved.policy_key == "이름만 있는 정책"


def test_run_recommendation_batch_for_all_users_skips_users_with_incomplete_profile(db_session, monkeypatch):
    _make_user(db_session, email="f@example.com", age=None)
    complete_user = _make_user(db_session, email="g@example.com")
    monkeypatch.setattr(recommender, "fetch_policies", lambda query=None: [_policy(policy_id="P004")])
    total = recommender.run_recommendation_batch_for_all_users(db_session)
    assert total == 1
    saved = db_session.query(PolicyRecommendation).one()
    assert saved.user_id == complete_user.id


def test_run_recommendation_batch_for_all_users_continues_after_one_user_errors(db_session, monkeypatch):
    _make_user(db_session, email="h@example.com")
    _make_user(db_session, email="i@example.com")

    calls = []

    def flaky_fetch(query=None):
        calls.append(query)
        if len(calls) == 1:
            raise RuntimeError("boom")
        return [_policy(policy_id="P005")]

    monkeypatch.setattr(recommender, "fetch_policies", flaky_fetch)
    total = recommender.run_recommendation_batch_for_all_users(db_session)
    assert len(calls) == 2
    assert total == 1
    assert db_session.query(PolicyRecommendation).count() == 1
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run (from `backend/`): `.venv/Scripts/pytest tests/features/test_recommender.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.features.policy_matcher.models'` (또는 `recommender`)

- [ ] **Step 3: `app/features/policy_matcher/models.py` 작성**

```python
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint

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
    matched_at = Column(DateTime, nullable=False)
```

- [ ] **Step 4: `app/features/policy_matcher/recommender.py` 작성**

```python
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.auth.models import User
from app.features.policy_matcher.matching import is_eligible
from app.features.policy_matcher.models import PolicyRecommendation
from app.features.policy_matcher.schemas import PolicyMatchInput
from app.features.policy_matcher.youth_center_client import fetch_policies

logger = logging.getLogger(__name__)


def _has_complete_profile(user: User) -> bool:
    return (
        user.age is not None
        and user.is_married is not None
        and user.annual_income_krw is not None
        and user.region is not None
    )


def run_recommendation_batch_for_user(db: Session, user: User) -> int:
    if not _has_complete_profile(user):
        return 0

    match_input = PolicyMatchInput(
        age=user.age,
        is_married=user.is_married,
        annual_income_krw=user.annual_income_krw,
        region=user.region,
    )
    policies = fetch_policies(query=user.region)

    existing_keys = {
        row.policy_key
        for row in db.query(PolicyRecommendation.policy_key).filter(PolicyRecommendation.user_id == user.id)
    }

    created = 0
    for policy in policies:
        if not is_eligible(policy, match_input):
            continue
        policy_key = policy.policy_id or policy.policy_name
        if policy_key in existing_keys:
            continue
        db.add(
            PolicyRecommendation(
                user_id=user.id,
                policy_key=policy_key,
                policy_name=policy.policy_name,
                benefit_description=policy.description,
                application_period=policy.application_period,
                reference_url=policy.apply_url,
                matched_at=datetime.now(timezone.utc),
            )
        )
        existing_keys.add(policy_key)
        created += 1

    db.commit()
    return created


def run_recommendation_batch_for_all_users(db: Session) -> int:
    total_created = 0
    users = db.query(User).all()
    for user in users:
        if not _has_complete_profile(user):
            continue
        try:
            total_created += run_recommendation_batch_for_user(db, user)
        except Exception:
            logger.exception("policy recommendation batch failed for user_id=%s", user.id)
            db.rollback()
    return total_created
```

(`run_recommendation_batch_for_all_users`의 `except Exception` + `db.rollback()`은 Global Constraints에서 설명한 의도적 예외다 — 한 유저 처리 중 실패해도 세션을 정리하고 다음 유저로 계속 진행한다.)

- [ ] **Step 5: `app/main.py`에 `PolicyRecommendation` 테이블 등록 import 추가**

`from app.features import register_all_tools` 줄 바로 아래(알파벳 순서상 그 다음 자리)에 추가:

```python
from app.features.policy_matcher.models import PolicyRecommendation  # noqa: F401
```

- [ ] **Step 6: 테스트 통과 확인**

Run (from `backend/`): `.venv/Scripts/pytest tests/features/test_recommender.py -v`
Expected: PASS (7 tests)

- [ ] **Step 7: 전체 백엔드 테스트 실행해 회귀 없는지 확인**

Run (from `backend/`): `.venv/Scripts/pytest -v`
Expected: PASS 전체

- [ ] **Step 8: Commit**

```bash
git add backend/app/features/policy_matcher/models.py backend/app/features/policy_matcher/recommender.py backend/app/main.py backend/tests/features/test_recommender.py
git commit -m "feat: add PolicyRecommendation table and recommendation batch engine"
```

---

## Task 5: 추천 조회/수동 갱신 API (`policy_matcher` 라우터)

**Files:**
- Modify: `backend/app/features/policy_matcher/schemas.py`
- Create: `backend/app/features/policy_matcher/router.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/features/test_policy_matcher_router.py`

**Interfaces:**
- Consumes: `recommender.run_recommendation_batch_for_user` (Task 4), `app.auth.router.get_current_user` (기존)
- Produces: 라우트 `POST /policy_matcher/recommendations/refresh` (인증 필요, `RefreshResponse` 반환)
- Produces: 라우트 `GET /policy_matcher/recommendations` (인증 필요, `RecommendationListResponse` 반환)

- [ ] **Step 1: 실패하는 테스트를 `backend/tests/features/test_policy_matcher_router.py`에 작성**

```python
from app.features.policy_matcher import recommender
from app.features.policy_matcher.youth_center_client import RawYouthPolicy


def _signup_login_with_profile(client, email="router-user@example.com"):
    client.post("/auth/signup", json={"email": email, "password": "secret123"})
    login = client.post("/auth/login", json={"email": email, "password": "secret123"})
    token = login.json()["access_token"]
    client.put(
        "/auth/profile",
        json={"age": 29, "is_married": False, "annual_income_krw": 40_000_000, "region": "서울"},
        headers={"Authorization": f"Bearer {token}"},
    )
    return token


def _policy(**overrides) -> RawYouthPolicy:
    defaults = dict(
        policy_id="P100",
        policy_name="테스트 정책",
        description="지원 내용",
        apply_url="https://example.com",
        application_period="상시",
        min_age=None,
        max_age=None,
        min_income_krw=None,
        max_income_krw=None,
        marital_status="",
        region_code="",
    )
    defaults.update(overrides)
    return RawYouthPolicy(**defaults)


def test_refresh_requires_auth(client):
    response = client.post("/policy_matcher/recommendations/refresh")
    assert response.status_code == 401


def test_refresh_creates_recommendations_for_eligible_policies(client, monkeypatch):
    monkeypatch.setattr(recommender, "fetch_policies", lambda query=None: [_policy()])
    token = _signup_login_with_profile(client)
    response = client.post(
        "/policy_matcher/recommendations/refresh",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["created"] == 1


def test_refresh_returns_zero_when_profile_incomplete(client, monkeypatch):
    monkeypatch.setattr(recommender, "fetch_policies", lambda query=None: [_policy()])
    client.post("/auth/signup", json={"email": "incomplete@example.com", "password": "secret123"})
    login = client.post("/auth/login", json={"email": "incomplete@example.com", "password": "secret123"})
    token = login.json()["access_token"]
    response = client.post(
        "/policy_matcher/recommendations/refresh",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["created"] == 0


def test_list_returns_only_current_users_recommendations(client, monkeypatch):
    monkeypatch.setattr(recommender, "fetch_policies", lambda query=None: [_policy(policy_id="P200")])
    token_a = _signup_login_with_profile(client, email="user-a@example.com")
    client.post("/policy_matcher/recommendations/refresh", headers={"Authorization": f"Bearer {token_a}"})

    token_b = _signup_login_with_profile(client, email="user-b@example.com")

    response_b = client.get("/policy_matcher/recommendations", headers={"Authorization": f"Bearer {token_b}"})
    assert response_b.status_code == 200
    assert response_b.json()["recommendations"] == []

    response_a = client.get("/policy_matcher/recommendations", headers={"Authorization": f"Bearer {token_a}"})
    assert len(response_a.json()["recommendations"]) == 1
    assert response_a.json()["recommendations"][0]["policy_name"] == "테스트 정책"
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run (from `backend/`): `.venv/Scripts/pytest tests/features/test_policy_matcher_router.py -v`
Expected: FAIL — `404 Not Found` (라우트가 아직 없음)

- [ ] **Step 3: `app/features/policy_matcher/schemas.py`에 응답 스키마 추가**

파일 상단 import에 `datetime` 추가하고, 파일 끝에 추가:

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict
```

```python
class RecommendationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    policy_name: str
    benefit_description: str
    application_period: str
    reference_url: str
    matched_at: datetime


class RecommendationListResponse(BaseModel):
    recommendations: list[RecommendationOut]


class RefreshResponse(BaseModel):
    created: int
```

- [ ] **Step 4: `app/features/policy_matcher/router.py` 작성**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.router import get_current_user
from app.core.db import get_db
from app.features.policy_matcher.models import PolicyRecommendation
from app.features.policy_matcher.recommender import run_recommendation_batch_for_user
from app.features.policy_matcher.schemas import RecommendationListResponse, RecommendationOut, RefreshResponse

router = APIRouter()


@router.post("/recommendations/refresh", response_model=RefreshResponse)
def refresh_my_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    created = run_recommendation_batch_for_user(db, current_user)
    return RefreshResponse(created=created)


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
    return RecommendationListResponse(recommendations=[RecommendationOut.model_validate(r) for r in rows])
```

- [ ] **Step 5: `app/main.py`에 라우터 등록**

`from app.features.policy_matcher.models import PolicyRecommendation` 줄 바로 아래(알파벳 순서상 그 다음 자리)에 추가:

```python
from app.features.policy_matcher.router import router as policy_matcher_router
```

`app.include_router(tools_router, ...)` 바로 아래에 추가:

```python
app.include_router(policy_matcher_router, prefix="/policy_matcher", tags=["policy_matcher"])
```

- [ ] **Step 6: 테스트 통과 확인**

Run (from `backend/`): `.venv/Scripts/pytest tests/features/test_policy_matcher_router.py -v`
Expected: PASS (4 tests)

- [ ] **Step 7: 전체 백엔드 테스트 실행해 회귀 없는지 확인**

Run (from `backend/`): `.venv/Scripts/pytest -v`
Expected: PASS 전체

- [ ] **Step 8: Commit**

```bash
git add backend/app/features/policy_matcher/schemas.py backend/app/features/policy_matcher/router.py backend/app/main.py backend/tests/features/test_policy_matcher_router.py
git commit -m "feat: add recommendation refresh and list endpoints"
```

---

## Task 6: 일일 배치 스케줄러 (APScheduler)

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/app/features/policy_matcher/recommender.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/features/test_recommender.py`

**Interfaces:**
- Produces: `app.features.policy_matcher.recommender.scheduler` (APScheduler `BackgroundScheduler` 인스턴스)
- Produces: `app.features.policy_matcher.recommender.register_daily_recommendation_job() -> None`

- [ ] **Step 1: `requirements.txt`에 의존성 추가**

`httpx` 줄 다음에 추가:

```
apscheduler
```

- [ ] **Step 2: 의존성 설치**

Run (from `backend/`): `.venv/Scripts/pip install -r requirements.txt`

- [ ] **Step 3: 실패하는 테스트를 `test_recommender.py`에 추가**

파일 끝에 추가:

```python
def test_register_daily_recommendation_job_adds_job_to_scheduler():
    recommender.register_daily_recommendation_job()
    job_ids = {job.id for job in recommender.scheduler.get_jobs()}
    assert "daily_policy_recommendation" in job_ids
```

- [ ] **Step 4: 테스트가 실패하는지 확인**

Run (from `backend/`): `.venv/Scripts/pytest tests/features/test_recommender.py -v`
Expected: FAIL — `AttributeError: module 'app.features.policy_matcher.recommender' has no attribute 'register_daily_recommendation_job'`

- [ ] **Step 5: `recommender.py`에 스케줄러 코드 추가**

파일 상단 import에 추가:

```python
from apscheduler.schedulers.background import BackgroundScheduler

from app.core.db import SessionLocal
```

파일 끝에 추가:

```python
scheduler = BackgroundScheduler()


def _run_daily_recommendation_job() -> None:
    db = SessionLocal()
    try:
        run_recommendation_batch_for_all_users(db)
    finally:
        db.close()


def register_daily_recommendation_job() -> None:
    scheduler.add_job(
        _run_daily_recommendation_job,
        "cron",
        hour=3,
        id="daily_policy_recommendation",
        replace_existing=True,
    )
```

(`replace_existing=True`는 앱이 재시작되거나 이 함수가 여러 번 호출돼도 "잡이 이미 있다" 에러 없이 안전하게 재등록되도록 한다. 테스트에서 `register_daily_recommendation_job()`을 직접 호출할 뿐 `scheduler.start()`는 부르지 않으므로, 테스트 중 실제로 백그라운드 스레드가 돌지는 않는다 — Global Constraints에서 설명한 대로 "잡이 등록되는지"만 확인한다.)

- [ ] **Step 6: `app/main.py`의 `lifespan`에 스케줄러 기동/종료 연결**

`from app.features.policy_matcher.models import PolicyRecommendation` 줄과 `from app.features.policy_matcher.router import ...` 줄 사이(알파벳 순서상 `models` 다음, `router` 앞)에 추가:

```python
from app.features.policy_matcher.recommender import register_daily_recommendation_job, scheduler
```

`lifespan` 함수를 다음으로 교체:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    register_daily_recommendation_job()
    scheduler.start()
    yield
    scheduler.shutdown()
```

- [ ] **Step 7: 테스트 통과 확인**

Run (from `backend/`): `.venv/Scripts/pytest tests/features/test_recommender.py -v`
Expected: PASS (8 tests)

- [ ] **Step 8: 전체 백엔드 테스트 실행해 회귀 없는지 확인**

Run (from `backend/`): `.venv/Scripts/pytest -v`
Expected: PASS 전체 (`main.py`의 `lifespan` 변경이 서버 기동 자체를 깨지 않는지는 다음 단계에서 수동으로도 확인한다)

- [ ] **Step 9: 서버가 정상 기동하는지 수동 확인**

Run (from `backend/`): `.venv/Scripts/uvicorn app.main:app` 실행 후 `Ctrl+C`로 종료 — 기동/종료 시 예외 없이 깨끗하게 뜨고 내려가는지 확인. (APScheduler 관련 예외가 있다면 여기서 드러난다 — pytest의 `client` fixture는 FastAPI `lifespan`을 실행하지 않으므로 이 단계가 유일한 실제 기동 검증이다.)

- [ ] **Step 10: Commit**

```bash
git add backend/requirements.txt backend/app/features/policy_matcher/recommender.py backend/app/main.py backend/tests/features/test_recommender.py
git commit -m "feat: wire APScheduler to run the daily recommendation batch"
```

---

## Task 7: 프론트엔드 "추천" 탭

**Files:**
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/app/(app)/layout.tsx`
- Create: `frontend/app/(app)/recommendations/page.tsx`

**Interfaces:**
- Consumes: `PUT /auth/profile`, `GET /auth/me`, `POST /policy_matcher/recommendations/refresh`, `GET /policy_matcher/recommendations` (Task 1, 5)

- [ ] **Step 1: `frontend/lib/api.ts`에 타입과 함수 추가**

파일 끝에 추가:

```typescript
export type UserProfile = {
  id: number;
  email: string;
  age: number | null;
  is_married: boolean | null;
  annual_income_krw: number | null;
  region: string | null;
};

export type ProfileInput = {
  age: number;
  is_married: boolean;
  annual_income_krw: number;
  region: string;
};

export type Recommendation = {
  policy_name: string;
  benefit_description: string;
  application_period: string;
  reference_url: string;
  matched_at: string;
};

type RecommendationListResponse = {
  recommendations: Recommendation[];
};

async function authedFetch(path: string, token: string, options: RequestInit = {}): Promise<Response> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      Authorization: `Bearer ${token}`,
      ...options.headers,
    },
  });
  if (!res.ok) {
    let detail = "요청이 실패했습니다.";
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // response body wasn't JSON — keep the generic message
    }
    throw new Error(detail);
  }
  return res;
}

export async function getMe(token: string): Promise<UserProfile> {
  const res = await authedFetch("/auth/me", token);
  return res.json();
}

export async function updateProfile(token: string, profile: ProfileInput): Promise<UserProfile> {
  const res = await authedFetch("/auth/profile", token, {
    method: "PUT",
    body: JSON.stringify(profile),
  });
  return res.json();
}

export async function getRecommendations(token: string): Promise<RecommendationListResponse> {
  const res = await authedFetch("/policy_matcher/recommendations", token);
  return res.json();
}

export async function refreshRecommendations(token: string): Promise<{ created: number }> {
  const res = await authedFetch("/policy_matcher/recommendations/refresh", token, { method: "POST" });
  return res.json();
}
```

(`authedFetch`는 새로 추가하는 4개 함수가 공유하는 인증+에러 처리 헬퍼다 — 기존 `callTool`의 에러 처리 방식과 동일하게 맞췄다. 기존 `login`/`callTool`은 건드리지 않는다.)

- [ ] **Step 2: `frontend/app/(app)/recommendations/page.tsx` 작성**

```tsx
"use client";

import { useEffect, useState } from "react";
import { getMe, getRecommendations, refreshRecommendations, updateProfile } from "@/lib/api";
import type { Recommendation, UserProfile } from "@/lib/api";

function hasCompleteProfile(profile: UserProfile | null): boolean {
  return (
    profile !== null &&
    profile.age !== null &&
    profile.is_married !== null &&
    profile.annual_income_krw !== null &&
    profile.region !== null
  );
}

export default function RecommendationsPage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [recommendations, setRecommendations] = useState<Recommendation[] | null>(null);
  const [age, setAge] = useState("29");
  const [isMarried, setIsMarried] = useState(false);
  const [income, setIncome] = useState("40000000");
  const [region, setRegion] = useState("서울");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function loadProfileAndRecommendations() {
    const token = localStorage.getItem("token") ?? "";
    const me = await getMe(token);
    setProfile(me);
    if (hasCompleteProfile(me)) {
      const list = await getRecommendations(token);
      setRecommendations(list.recommendations);
    }
  }

  useEffect(() => {
    loadProfileAndRecommendations().catch((err) => {
      setError(err instanceof Error ? err.message : "불러오기에 실패했습니다.");
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleProfileSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    const token = localStorage.getItem("token") ?? "";
    try {
      await updateProfile(token, {
        age: Number(age),
        is_married: isMarried,
        annual_income_krw: Number(income),
        region,
      });
      await loadProfileAndRecommendations();
    } catch (err) {
      setError(err instanceof Error ? err.message : "프로필 저장에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  }

  async function handleRefresh() {
    setError(null);
    setLoading(true);
    const token = localStorage.getItem("token") ?? "";
    try {
      await refreshRecommendations(token);
      const list = await getRecommendations(token);
      setRecommendations(list.recommendations);
    } catch (err) {
      setError(err instanceof Error ? err.message : "추천 갱신에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <div className="page-header">
        <h1>🔔 맞춤 추천</h1>
        <p>프로필을 저장해두면 매일 새로 맞는 정책을 찾아 알려드립니다.</p>
      </div>

      {error && <p className="error-text" style={{ marginTop: 16 }}>{error}</p>}

      {!hasCompleteProfile(profile) && (
        <div className="card">
          <form onSubmit={handleProfileSubmit}>
            <label className="field">
              <span className="field-label">나이</span>
              <input className="input" type="number" value={age} onChange={(e) => setAge(e.target.value)} />
            </label>
            <label className="checkbox-field">
              <input type="checkbox" checked={isMarried} onChange={(e) => setIsMarried(e.target.checked)} />
              기혼
            </label>
            <label className="field">
              <span className="field-label">연소득 (원)</span>
              <input className="input" type="number" value={income} onChange={(e) => setIncome(e.target.value)} />
            </label>
            <label className="field">
              <span className="field-label">지역</span>
              <input className="input" type="text" value={region} onChange={(e) => setRegion(e.target.value)} />
            </label>
            <button className="btn" type="submit" disabled={loading}>
              {loading ? "저장 중..." : "프로필 저장하고 추천 받기"}
            </button>
          </form>
        </div>
      )}

      {hasCompleteProfile(profile) && (
        <>
          <button className="btn" onClick={handleRefresh} disabled={loading} style={{ marginBottom: 16 }}>
            {loading ? "갱신 중..." : "지금 갱신"}
          </button>

          {recommendations && recommendations.length === 0 && (
            <p className="error-text">아직 추천된 정책이 없습니다. &quot;지금 갱신&quot;을 눌러보세요.</p>
          )}

          {recommendations && recommendations.length > 0 && (
            <div className="result-list">
              {recommendations.map((rec, i) => (
                <div key={i} className="result-item">
                  <div className="result-item-title">{rec.policy_name}</div>
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
            </div>
          )}
        </>
      )}
    </>
  );
}
```

- [ ] **Step 3: `frontend/app/(app)/layout.tsx`의 `TABS`에 새 탭 추가**

```typescript
const TABS = [
  { href: "/policy", label: "정책비교", icon: "🏛️" },
  { href: "/savings", label: "저축플랜", icon: "💰" },
  { href: "/subscriptions", label: "구독료 리포트", icon: "📺" },
  { href: "/cards", label: "카드소비 리포트", icon: "💳" },
  { href: "/recommendations", label: "추천", icon: "🔔" },
];
```

- [ ] **Step 4: 타입체크로 검증**

Run (from `frontend/`): `npm run build`
Expected: 빌드 성공 (타입 에러 없음)

- [ ] **Step 5: Commit**

```bash
git add "frontend/lib/api.ts" "frontend/app/(app)/layout.tsx" "frontend/app/(app)/recommendations/page.tsx"
git commit -m "feat: add recommendations tab with profile form and refresh button"
```

---

## 최종 확인

- [ ] **Step 1: 백엔드 전체 테스트 재실행**

Run (from `backend/`): `.venv/Scripts/pytest -v`
Expected: PASS, 실패 0

- [ ] **Step 2: 프론트엔드 빌드 재확인**

Run (from `frontend/`): `npm run build`
Expected: 빌드 성공

- [ ] **Step 3: 서버 기동 확인**

Run (from `backend/`): `.venv/Scripts/uvicorn app.main:app` 실행 후 `Ctrl+C`로 종료 — 예외 없이 기동/종료되는지 최종 확인.
