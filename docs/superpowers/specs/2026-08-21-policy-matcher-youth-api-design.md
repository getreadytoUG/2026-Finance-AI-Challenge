# policy_matcher 실제 데이터 연동 설계 — 온통청년 Open API

## 배경 및 목표

`policy_matcher`는 현재 `age <= 34`만 검사하고 정책 1개("청년 전세자금대출 (샘플 데이터)")를 고정 반환하는 placeholder 상태다([backend/app/features/policy_matcher/tool.py](../../../backend/app/features/policy_matcher/tool.py)). 이 스펙은 이를 실제 정부 공개 데이터를 기반으로 한 다중 정책·다중 조건 매칭으로 대체하는 것을 목표로 한다.

4개 기능 중 실제 데이터 연동의 첫 번째 대상으로 `policy_matcher`를 선택했다 (공공데이터 API 활용도가 가장 높고, 실은행 API 승인 절차가 필요 없음). 나머지 3개 기능(`savings_planner`, `subscription_report`, `card_spending_report`)은 이 스펙 범위 밖이며, 각각 별도로 브레인스토밍한다.

## 범위

**포함**: `policy_matcher`의 `run()`을 온통청년 Open API 실호출 기반으로 재작성. 정책 데이터 fetch, XML 파싱, 다중 조건 매칭 로직, 출력 스키마 변경, 프론트엔드 표시 변경.

**포함하지 않음**: 다른 3개 기능, apibazzar 연동, 정책 데이터 캐싱/배치 갱신(추후 필요시 별도 스펙).

## 데이터 소스: 온통청년 Open API

- 발급처: 온통청년(청년정책통합정보시스템), `https://www.youthcenter.go.kr`
- 엔드포인트: `https://www.youthcenter.go.kr/opi/youthPlcyList.do`
- 응답 포맷: XML
- 요청 파라미터(공식 문서 확인): `openApiVlak`(인증키), `pageIndex`, `display`(페이지당 건수), `query`(검색어), `bizTycdSel`, `srchPolyBizSecd`, `keyword`
- 이용자는 온통청년 회원가입 → 마이페이지 → OPEN API 발급 신청(관리자 승인제) 절차로 키를 받는다.

**⚠️ 리스크: 응답 필드명 미검증.** 요청 파라미터는 공식 문서에서 확인했지만, 실제 키가 없어 라이브 응답을 볼 수 없었다. 이 스펙은 공개된 필드 관례(나이 상/하한, 소득 조건, 혼인상태 코드, 지역 코드 등)를 최선으로 추정해 구현하되, 파싱을 `_parse_youth_policy_xml()` 한 함수에 격리한다. 실제 키 발급 후 라이브 응답 샘플을 확보하면 이 함수만 수정하면 되도록 만드는 것이 이 설계의 핵심 결정이다.

## 아키텍처

### 새 모듈: `app/features/policy_matcher/youth_center_client.py`

```python
def fetch_policies(query: str | None = None, page_index: int = 1, display: int = 100) -> list[RawYouthPolicy]:
    """온통청년 API를 호출해 원시 정책 레코드 목록을 반환한다."""

def _parse_youth_policy_xml(xml_text: str) -> list[RawYouthPolicy]:
    """XML 응답을 RawYouthPolicy 리스트로 변환 — 필드 매핑 불확실성이 격리되는 지점."""
```

- HTTP 클라이언트: `httpx` (이미 `requirements.txt`에 있음, 새 의존성 없음)
- XML 파싱: 표준 라이브러리 `xml.etree.ElementTree`
- `RawYouthPolicy`: 정책명, 설명, 신청 URL, 신청 기간, 최소/최대 연령, 소득 조건 텍스트, 혼인상태 코드, 지역 코드를 담는 내부 pydantic 모델 (API 응답과 우리 스키마 사이의 중간 표현)

### 설정: `app/core/config.py`

- `youth_center_api_key: str = ""` 필드 추가
- `.env.example`에 `YOUTH_CENTER_API_KEY=` 추가, README에 발급 절차 안내 추가

### 매칭 로직: `app/features/policy_matcher/tool.py`

`run()`이 하던 일:
1. `fetch_policies()`로 정책 목록 조회 (지역 검색어로 `query` 파라미터 활용)
2. 각 정책에 대해 나이/소득/혼인상태 조건을 사용자 입력과 비교해 `eligible` 판정
3. 조건 정보가 없는 정책(전체 대상)은 무조건 `eligible=True`로 처리
4. 매칭된 정책들을 `PolicyMatchOutput`으로 변환해 반환

API 호출 실패(키 미설정, 네트워크 오류, 4xx/5xx)는 예외를 그대로 던진다 — `ToolRegistry.execute()`가 이미 `ToolExecutionError`로 감싸 400으로 응답하는 경로가 있으므로 별도 처리가 필요 없다([backend/app/tools/router.py](../../../backend/app/tools/router.py)). 즉 이 기능은 유효한 `YOUTH_CENTER_API_KEY` 없이는 동작하지 않는다 — 로컬 개발/데모에는 실제 키가 필요하다.

## 스키마 변경 (Breaking)

현재 `PolicyOption`:

```python
class PolicyOption(BaseModel):
    policy_name: str
    eligible: bool
    preferential_rate_percent: float
    reference_url: str
```

`preferential_rate_percent`(우대금리)는 주거 대출 상품 전용 개념이라 온통청년 API가 다루는 일자리/주거/교육/복지/참여권리 전체 정책군에 맞지 않는다. 다음으로 변경:

```python
class PolicyOption(BaseModel):
    policy_name: str
    eligible: bool
    benefit_description: str    # 지원 내용 요약
    application_period: str     # 신청 기간 (상시/기간 미표기 시 "상시")
    reference_url: str
```

### 프론트엔드 영향

[frontend/app/(app)/policy/page.tsx](../../../frontend/app/(app)/policy/page.tsx) 의 `PolicyOption` 타입과 결과 렌더링부(현재 `preferential_rate_percent`를 `%`로 표시하는 부분)를 `benefit_description`/`application_period` 표시로 교체한다.

## 데이터 흐름

1. 사용자가 프론트에서 나이/혼인여부/소득/지역 입력 → `POST /tools/policy_matcher`
2. `run()`이 `fetch_policies(query=region)` 호출 (지역을 `query` 자유검색어로 넘기는 것도 응답 필드명과 마찬가지로 최선 추정이다 — 라이브 응답에서 지역 전용 파라미터/코드 체계가 확인되면 이 호출부만 바꾸면 되도록 `youth_center_client.py`에 격리한다)
3. 온통청년 API가 XML 응답 → `_parse_youth_policy_xml()`이 `RawYouthPolicy` 리스트로 변환
4. 매칭 로직이 각 정책의 연령/소득/혼인 조건을 사용자 입력과 비교
5. `PolicyMatchOutput` 반환 → 프론트가 지원 내용/신청 기간/링크로 렌더링

## 에러 처리

- API 키 미설정, 네트워크 오류, 비정상 XML → 예외 발생 → `ToolExecutionError` → 클라이언트 400 (기존 패턴 재사용, 새 처리 불필요)
- 정책 레코드에 조건 필드가 없는 경우(전체 대상 정책) → 매칭 로직에서 무조건 `eligible=True`로 처리 (필드 누락을 "조건 없음"으로 해석)

## 테스트

- `youth_center_client.py`: 합성 XML 샘플(2~3개 정책, 조건 있는 것/없는 것 혼합)로 `_parse_youth_policy_xml()` 단위 테스트
- `tool.py`의 `run()`: `fetch_policies`를 monkeypatch로 대체해 매칭 로직만 검증 (나이 초과 시 불가, 혼인 조건 미충족 시 불가, 조건 없는 정책은 항상 가능 등) — 기존 `tests/features/test_policy_matcher.py`의 3개 테스트를 이 방식으로 재작성
- 실제 라이브 API 호출은 테스트에서 하지 않음 (키 필요, 네트워크 의존성)

## 사용자가 해야 할 일

1. 온통청년(https://www.youthcenter.go.kr) 회원가입
2. 로그인 후 마이페이지 → OPEN API 메뉴에서 발급 신청 (승인 대기 필요, 소요 시간은 온통청년 운영진에 달림)
3. 발급된 키를 `backend/.env`의 `YOUTH_CENTER_API_KEY`에 입력 (구현 완료 후 안내)
4. 승인 전까지는 이 기능이 로컬에서 동작하지 않음 — 테스트는 mock을 쓰므로 키 없이도 통과함
