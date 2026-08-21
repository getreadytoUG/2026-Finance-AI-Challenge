# policy_matcher 실제 데이터 연동 (온통청년 Open API) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `policy_matcher`의 `run()`을 고정 샘플 데이터 대신 온통청년(청년정책통합정보시스템) Open API 실호출과 다중 조건(나이/소득/혼인여부/지역) 매칭 로직으로 교체한다.

**Architecture:** 신규 `youth_center_client.py`가 온통청년 API를 호출해 XML을 파싱하고 `RawYouthPolicy` 리스트로 반환한다. `tool.py`의 `run()`이 이 리스트를 사용자 입력과 비교해 정책별 `eligible` 여부를 판정한다. API 응답 필드명은 공식 문서로 검증하지 못했으므로 파싱은 `_parse_youth_policy_xml()` 한 함수에 격리하고, 나머지 코드는 `RawYouthPolicy`의 의미론적 필드(연령/소득/혼인상태/지역)에만 의존한다.

**Tech Stack:** 기존 `httpx`(신규 의존성 없음), 표준 라이브러리 `xml.etree.ElementTree`, pytest + `monkeypatch`.

**Spec:** [docs/superpowers/specs/2026-08-21-policy-matcher-youth-api-design.md](../specs/2026-08-21-policy-matcher-youth-api-design.md)

## Global Constraints

- API 엔드포인트: `https://www.youthcenter.go.kr/opi/youthPlcyList.do`, 인증 파라미터명은 `openApiVlak`, 응답은 XML.
- 응답 XML의 정확한 필드명은 미검증 — `_parse_youth_policy_xml()`에서만 다루고 나머지 코드는 `RawYouthPolicy`의 의미론적 필드명에 의존한다.
- API 호출 실패는 그대로 예외를 던진다 — `ToolRegistry.execute()`가 이미 `ToolExecutionError`로 감싸 400 응답하는 경로가 있으므로 `run()`/`youth_center_client.py`에서 별도 try/except를 추가하지 않는다.
- `PolicyOption`에서 `preferential_rate_percent`를 제거하고 `benefit_description`, `application_period`로 교체한다 (breaking change, 프론트엔드도 함께 수정).
- 정책 데이터 fetch는 온통청년 API가 유일한 소스다 (샘플/폴백 데이터 없음) — 실제 키 없이는 이 기능이 로컬에서 동작하지 않는다.

---

## Task 1: 설정 — `youth_center_api_key` + 발급 안내 문서

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `backend/.env.example`
- Modify: `README.md`

**Interfaces:**
- Produces: `app.core.config.settings.youth_center_api_key: str` — Task 2에서 `youth_center_client.py`가 이 값을 읽어 API 호출 인증에 사용

- [ ] **Step 1: `Settings`에 필드 추가**

[backend/app/core/config.py](../../../backend/app/core/config.py)의 `Settings` 클래스에 다음 필드를 `cors_origins` 다음 줄에 추가:

```python
    youth_center_api_key: str = ""
```

- [ ] **Step 2: `.env.example`에 항목 추가**

[backend/.env.example](../../../backend/.env.example) 끝에 추가:

```
# 온통청년(청년정책통합정보시스템) Open API 인증키.
# 발급 방법: README.md의 "policy_matcher — 온통청년 API 키 발급" 절 참고.
YOUTH_CENTER_API_KEY=
```

- [ ] **Step 3: README에 발급 안내 절 추가**

[README.md](../../../README.md)의 `## 현재 범위 밖 (다음 단계)` 섹션 바로 위에 다음 절을 추가:

```markdown
## policy_matcher — 온통청년 API 키 발급

`policy_matcher` 기능은 온통청년(청년정책통합정보시스템) Open API를 실호출합니다. 키 없이는 이 기능이 동작하지 않습니다.

1. https://www.youthcenter.go.kr 에서 회원가입
2. 로그인 후 마이페이지 → OPEN API 메뉴에서 인증키 발급 신청 (관리자 승인제)
3. 승인된 키를 `backend/.env`의 `YOUTH_CENTER_API_KEY`에 입력
4. 키가 없어도 `pytest`는 통과합니다 (API 호출을 mock으로 대체) — 실제 `/tools/policy_matcher` 호출에만 키가 필요합니다
```

- [ ] **Step 4: 전체 테스트 실행해 회귀 없는지 확인**

Run (from `backend/`): `.venv/Scripts/pytest -v`
Expected: PASS (기존 37개 테스트 전부, 필드 추가만으로는 아무것도 깨지지 않음)

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/config.py backend/.env.example README.md
git commit -m "chore: add YOUTH_CENTER_API_KEY setting and acquisition docs"
```

---

## Task 2: 온통청년 API 클라이언트 (`youth_center_client.py`)

**Files:**
- Create: `backend/app/features/policy_matcher/youth_center_client.py`
- Test: `backend/tests/features/test_youth_center_client.py`

**Interfaces:**
- Consumes: `app.core.config.settings.youth_center_api_key` (Task 1)
- Produces: `app.features.policy_matcher.youth_center_client.RawYouthPolicy(policy_name: str, description: str, apply_url: str, application_period: str, min_age: int | None, max_age: int | None, min_income_krw: int | None, max_income_krw: int | None, marital_status: str, region_code: str)` — Task 3의 매칭 로직이 이 필드들만 사용
- Produces: `app.features.policy_matcher.youth_center_client.fetch_policies(query: str | None = None, page_index: int = 1, display: int = 100) -> list[RawYouthPolicy]` — Task 3이 호출
- Produces: `app.features.policy_matcher.youth_center_client._parse_youth_policy_xml(xml_text: str) -> list[RawYouthPolicy]` — 응답 필드명 불확실성이 격리되는 지점 (추후 실제 응답 샘플 확보 시 이 함수만 수정)

- [ ] **Step 1: 실패하는 테스트를 `backend/tests/features/test_youth_center_client.py`에 작성**

```python
import httpx

from app.features.policy_matcher import youth_center_client
from app.features.policy_matcher.youth_center_client import (
    RawYouthPolicy,
    _parse_youth_policy_xml,
    fetch_policies,
)

SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<youthPolicyList>
  <youthPolicy>
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


def test_parse_youth_policy_xml_parses_full_record():
    policies = _parse_youth_policy_xml(SAMPLE_XML)
    first = policies[0]
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


def test_parse_youth_policy_xml_defaults_missing_fields_to_none_or_empty():
    policies = _parse_youth_policy_xml(SAMPLE_XML)
    second = policies[1]
    assert second.marital_status == "기혼"
    assert second.min_age is None
    assert second.max_age is None
    assert second.application_period == "상시"
    assert second.region_code == ""


def test_parse_youth_policy_xml_returns_all_items():
    policies = _parse_youth_policy_xml(SAMPLE_XML)
    assert len(policies) == 2


def test_fetch_policies_calls_api_with_key_and_query_and_parses_response(monkeypatch):
    monkeypatch.setattr(youth_center_client.settings, "youth_center_api_key", "test-key")

    captured = {}

    def fake_get(url, params, timeout):
        captured["url"] = url
        captured["params"] = params
        return httpx.Response(status_code=200, text=SAMPLE_XML, request=httpx.Request("GET", url))

    monkeypatch.setattr(youth_center_client.httpx, "get", fake_get)

    policies = fetch_policies(query="서울")

    assert captured["url"] == "https://www.youthcenter.go.kr/opi/youthPlcyList.do"
    assert captured["params"]["openApiVlak"] == "test-key"
    assert captured["params"]["query"] == "서울"
    assert len(policies) == 2
    assert policies[0].policy_name == "청년 월세 지원"


def test_fetch_policies_raises_on_http_error(monkeypatch):
    monkeypatch.setattr(youth_center_client.settings, "youth_center_api_key", "test-key")

    def fake_get(url, params, timeout):
        return httpx.Response(status_code=500, text="server error", request=httpx.Request("GET", url))

    monkeypatch.setattr(youth_center_client.httpx, "get", fake_get)

    try:
        fetch_policies()
        assert False, "expected httpx.HTTPStatusError"
    except httpx.HTTPStatusError:
        pass
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run (from `backend/`): `.venv/Scripts/pytest tests/features/test_youth_center_client.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.features.policy_matcher.youth_center_client'`

- [ ] **Step 3: `app/features/policy_matcher/youth_center_client.py` 작성**

```python
import xml.etree.ElementTree as ET

import httpx
from pydantic import BaseModel

from app.core.config import settings

YOUTH_CENTER_API_URL = "https://www.youthcenter.go.kr/opi/youthPlcyList.do"


class RawYouthPolicy(BaseModel):
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


def fetch_policies(query: str | None = None, page_index: int = 1, display: int = 100) -> list[RawYouthPolicy]:
    params = {
        "openApiVlak": settings.youth_center_api_key,
        "pageIndex": page_index,
        "display": display,
    }
    if query:
        params["query"] = query
    response = httpx.get(YOUTH_CENTER_API_URL, params=params, timeout=10.0)
    response.raise_for_status()
    return _parse_youth_policy_xml(response.text)


# NOTE: 아래 태그명(plcyNm, plcyExplnCn, sprtTrgtMinAge, mrgSttsCd 등)은 온통청년
# 공식 문서에서 요청 파라미터만 확인했고 실제 응답 필드명은 검증하지 못했다.
# 실제 API 키로 라이브 응답 샘플을 확보하면 이 함수의 _text() 호출부만 수정하면 된다.
def _parse_youth_policy_xml(xml_text: str) -> list[RawYouthPolicy]:
    root = ET.fromstring(xml_text)
    policies = []
    for item in root.iter("youthPolicy"):
        policies.append(
            RawYouthPolicy(
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
        )
    return policies


def _text(item: ET.Element, tag: str) -> str:
    el = item.find(tag)
    return el.text.strip() if el is not None and el.text else ""


def _int_or_none(value: str) -> int | None:
    return int(value) if value.isdigit() else None
```

- [ ] **Step 4: 테스트 통과 확인**

Run (from `backend/`): `.venv/Scripts/pytest tests/features/test_youth_center_client.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/features/policy_matcher/youth_center_client.py backend/tests/features/test_youth_center_client.py
git commit -m "feat: add Youth Center API client (fetch + XML parsing) for policy_matcher"
```

---

## Task 3: 매칭 로직 재작성 + 스키마 변경 (`schemas.py`, `tool.py`)

**Files:**
- Modify: `backend/app/features/policy_matcher/schemas.py`
- Modify: `backend/app/features/policy_matcher/tool.py`
- Modify: `backend/tests/features/test_policy_matcher.py`

**Interfaces:**
- Consumes: `app.features.policy_matcher.youth_center_client.RawYouthPolicy`, `fetch_policies` (Task 2)
- Produces: `app.features.policy_matcher.schemas.PolicyOption(policy_name: str, eligible: bool, benefit_description: str, application_period: str, reference_url: str)` — **breaking change**, Task 4(프론트엔드)가 이 필드명에 맞춰야 함
- Produces: `app.features.policy_matcher.tool.run(input: PolicyMatchInput, ctx: ToolContext) -> PolicyMatchOutput` (기존 시그니처 유지, 내부 로직만 교체)

- [ ] **Step 1: 실패하는 테스트로 `backend/tests/features/test_policy_matcher.py` 전체 교체**

```python
from app.features.policy_matcher import tool
from app.features.policy_matcher.schemas import PolicyMatchInput
from app.features.policy_matcher.tool import TOOL_SPEC, run
from app.features.policy_matcher.youth_center_client import RawYouthPolicy
from app.tools.base import ToolContext

CTX = ToolContext(user_id=1, db=None)


def _policy(**overrides) -> RawYouthPolicy:
    defaults = dict(
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


def test_tool_spec_has_expected_name_and_schemas():
    assert TOOL_SPEC.name == "policy_matcher"
    assert TOOL_SPEC.entrypoint is run


def test_run_marks_policy_without_conditions_always_eligible(monkeypatch):
    monkeypatch.setattr(tool, "fetch_policies", lambda query=None: [_policy()])
    result = run(PolicyMatchInput(age=29, is_married=False, annual_income_krw=40_000_000, region="서울"), CTX)
    assert result.options[0].eligible is True


def test_run_marks_applicant_outside_age_range_ineligible(monkeypatch):
    monkeypatch.setattr(tool, "fetch_policies", lambda query=None: [_policy(min_age=19, max_age=34)])
    result = run(PolicyMatchInput(age=50, is_married=False, annual_income_krw=40_000_000, region="서울"), CTX)
    assert result.options[0].eligible is False


def test_run_requires_marriage_when_policy_restricts_to_married(monkeypatch):
    monkeypatch.setattr(tool, "fetch_policies", lambda query=None: [_policy(marital_status="기혼")])
    single = run(PolicyMatchInput(age=29, is_married=False, annual_income_krw=40_000_000, region="서울"), CTX)
    married = run(PolicyMatchInput(age=29, is_married=True, annual_income_krw=40_000_000, region="서울"), CTX)
    assert single.options[0].eligible is False
    assert married.options[0].eligible is True


def test_run_marks_applicant_over_income_ceiling_ineligible(monkeypatch):
    monkeypatch.setattr(tool, "fetch_policies", lambda query=None: [_policy(max_income_krw=30_000_000)])
    result = run(PolicyMatchInput(age=29, is_married=False, annual_income_krw=40_000_000, region="서울"), CTX)
    assert result.options[0].eligible is False


def test_run_marks_applicant_below_income_floor_ineligible(monkeypatch):
    monkeypatch.setattr(tool, "fetch_policies", lambda query=None: [_policy(min_income_krw=50_000_000)])
    result = run(PolicyMatchInput(age=29, is_married=False, annual_income_krw=40_000_000, region="서울"), CTX)
    assert result.options[0].eligible is False


def test_run_marks_applicant_outside_region_ineligible(monkeypatch):
    monkeypatch.setattr(tool, "fetch_policies", lambda query=None: [_policy(region_code="부산")])
    result = run(PolicyMatchInput(age=29, is_married=False, annual_income_krw=40_000_000, region="서울"), CTX)
    assert result.options[0].eligible is False


def test_run_maps_policy_fields_into_output_option(monkeypatch):
    monkeypatch.setattr(
        tool,
        "fetch_policies",
        lambda query=None: [
            _policy(
                policy_name="청년 월세 지원",
                description="월 20만원 지원",
                apply_url="https://example.com/apply",
                application_period="2026-01-01 ~ 2026-12-31",
            )
        ],
    )
    result = run(PolicyMatchInput(age=29, is_married=False, annual_income_krw=40_000_000, region="서울"), CTX)
    option = result.options[0]
    assert option.policy_name == "청년 월세 지원"
    assert option.benefit_description == "월 20만원 지원"
    assert option.reference_url == "https://example.com/apply"
    assert option.application_period == "2026-01-01 ~ 2026-12-31"
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run (from `backend/`): `.venv/Scripts/pytest tests/features/test_policy_matcher.py -v`
Expected: FAIL — `AttributeError` 또는 `ImportError` (아직 `fetch_policies`를 쓰지 않고, `PolicyOption`에 `benefit_description`이 없음)

- [ ] **Step 3: `schemas.py` 교체**

```python
from pydantic import BaseModel


class PolicyMatchInput(BaseModel):
    age: int
    is_married: bool
    annual_income_krw: int
    region: str


class PolicyOption(BaseModel):
    policy_name: str
    eligible: bool
    benefit_description: str
    application_period: str
    reference_url: str


class PolicyMatchOutput(BaseModel):
    options: list[PolicyOption]
```

- [ ] **Step 4: `tool.py` 교체**

```python
from app.features.policy_matcher.schemas import PolicyMatchInput, PolicyMatchOutput, PolicyOption
from app.features.policy_matcher.youth_center_client import RawYouthPolicy, fetch_policies
from app.tools.base import ToolContext, ToolSpec


def _is_eligible(policy: RawYouthPolicy, input: PolicyMatchInput) -> bool:
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
    if policy.region_code and policy.region_code not in input.region and input.region not in policy.region_code:
        return False
    return True


def run(input: PolicyMatchInput, ctx: ToolContext) -> PolicyMatchOutput:
    policies = fetch_policies(query=input.region)
    options = [
        PolicyOption(
            policy_name=policy.policy_name,
            eligible=_is_eligible(policy, input),
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

- [ ] **Step 5: 테스트 통과 확인**

Run (from `backend/`): `.venv/Scripts/pytest tests/features/test_policy_matcher.py -v`
Expected: PASS (8 tests)

- [ ] **Step 6: 전체 백엔드 테스트 스위트 실행해 회귀 없는지 확인**

Run (from `backend/`): `.venv/Scripts/pytest -v`
Expected: PASS 전체 (Task 2에서 추가된 5개 + 이 Task의 8개 포함)

- [ ] **Step 7: Commit**

```bash
git add backend/app/features/policy_matcher/schemas.py backend/app/features/policy_matcher/tool.py backend/tests/features/test_policy_matcher.py
git commit -m "feat: replace policy_matcher placeholder with multi-condition Youth Center API matching"
```

---

## Task 4: 프론트엔드 정책비교 화면 업데이트

**Files:**
- Modify: `frontend/app/(app)/policy/page.tsx`

**Interfaces:**
- Consumes: `PolicyOption` 응답 필드 `policy_name`, `eligible`, `benefit_description`, `application_period`, `reference_url` (Task 3)

- [ ] **Step 1: `PolicyOption` 타입 업데이트**

[frontend/app/(app)/policy/page.tsx](../../../frontend/app/(app)/policy/page.tsx) 5-11번 줄의 타입을 교체:

```typescript
type PolicyOption = {
  policy_name: string;
  eligible: boolean;
  benefit_description: string;
  application_period: string;
  reference_url: string;
};
```

- [ ] **Step 2: 결과 렌더링 부분 업데이트**

91-94번 줄(우대금리 표시)을 교체:

```tsx
              <div className="result-item-row">
                <span>지원 내용</span>
                <span>{option.benefit_description}</span>
              </div>
              <div className="result-item-row">
                <span>신청 기간</span>
                <span>{option.application_period}</span>
              </div>
```

- [ ] **Step 3: 타입체크로 검증**

Run (from `frontend/`): `npm run build`
Expected: 빌드 성공 (타입 에러 없음) — `preferential_rate_percent`를 참조하는 곳이 남아있으면 TypeScript 컴파일 단계에서 실패한다.

- [ ] **Step 4: Commit**

```bash
git add "frontend/app/(app)/policy/page.tsx"
git commit -m "feat: update policy page to show benefit description and application period"
```

---

## 최종 확인

- [ ] **Step 1: 백엔드 전체 테스트 재실행**

Run (from `backend/`): `.venv/Scripts/pytest -v`
Expected: PASS 전체 (기존 37개 + 신규 13개 = 50개, `test_policy_matcher.py`의 기존 3개 테스트가 8개로 교체되었으므로 정확한 총합은 47 - 3 + 8 + 5 = 52개가 될 수 있음 — 정확한 숫자보다 "PASS, 실패 0"을 확인하는 것이 중요하다)

- [ ] **Step 2: 프론트엔드 빌드 재확인**

Run (from `frontend/`): `npm run build`
Expected: 빌드 성공
