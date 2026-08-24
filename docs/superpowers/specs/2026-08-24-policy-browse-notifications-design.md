# 정책 읽기 탭 + 추천 알림 배지 — 설계 문서

**작성일**: 2026-08-24
**관련 기획**: `md_files/기획서.md` 5장(정책), `md_files/PLAN.md`, `md_files/BACKLOG.md`

## 배경

지금 정책 관련 기능은 "정책비교"(개인 조건 대입 후 가/불가 판단)와 "추천"(일일
배치로 자동 매칭된 목록) 두 개뿐이다. 기획서가 요구하는 아래 3가지가 빠져 있다:

1. 조건 없이 전체 정책을 카테고리별로 그냥 훑어보는 "정책 읽기" 탭
2. 마감/임박 등 신청 상태를 한눈에 보여주는 배지
3. 새로 매칭된 추천 정책이 생겼을 때 눈에 띄는 알림(배지)

## 스코프

**포함**: 정책 캐시 테이블 + 배치, 정책 읽기 탭(카테고리 필터 + 상태 배지 + 페이지네이션),
추천 탭 미확인 배지(개별 클릭 시 읽음 처리).

**제외** (BACKLOG.md에 남는 별도 항목): 정책 상세 페이지, 정책 챗봇, 저축플랜 연결,
리포트 캐싱. 이번 스코프는 순수 "정책 읽기 + 알림"에 한정한다.

## 1. 데이터 계층

### 1.1 신규 테이블: `cached_policies`

```
id: Integer PK
policy_key: String, unique  # plcyNo, 없으면 policy_name (recommender.py와 동일 규칙)
policy_name: String
description: String
apply_url: String
application_period: String       # 사람이 읽는 텍스트 (예: "20260812 ~ 20260909", 없으면 "상시")
apply_start_ymd: String, nullable   # bizPrdBgngYmd 원본 (YYYYMMDD, 공백이면 None)
apply_end_ymd: String, nullable     # bizPrdEndYmd 원본 (YYYYMMDD, 공백이면 None)
large_category: String     # lclsfNm 원본 그대로 (예: "주거", "교육・직업훈련")
mid_category: String       # mclsfNm 원본
min_age, max_age: Integer, nullable
min_income_krw, max_income_krw: Integer, nullable
marital_status: String
region_code: String
refreshed_at: DateTime(timezone=True)
```

인덱스: `large_category`(필터 조회용).

### 1.2 온통청년 클라이언트 확장

`youth_center_client.py`에 `fetch_all_policies()`를 추가한다. 실측 결과
`pageSize=3000`으로 전체(~2,728건, 계속 늘어날 수 있음)를 **한 번의 HTTP
요청**으로 가져올 수 있었다(200 OK, 약 1.7초, 7.3MB). 페이지네이션 루프는
필요 없다 — `pageSize`를 넉넉히 크게(예: 5000) 잡아 한 번에 호출한다.

`_parse_youth_policy_json`이 이미 만드는 `RawYouthPolicy`에 없는 필드
(`lclsfNm`, `mclsfNm`, `bizPrdBgngYmd`, `bizPrdEndYmd`)가 필요하므로,
`RawYouthPolicy`를 확장하거나 이 값들을 담을 새 타입(`RawYouthPolicyDetail`
등)을 만든다 — 실제 판단은 구현 시 기존 `RawYouthPolicy` 소비처(matching.py,
tool.py, recommender.py)를 깨지 않는 방향으로 한다.

### 1.3 캐시 갱신 배치

기존 `recommender.py`의 매일 새벽 3시 스케줄 잡 안에서, 추천 배치를 돌리기
**전에** 캐시 갱신을 먼저 실행한다(같은 트리거, 새 스케줄 안 만듦):

```
_run_daily_recommendation_job():
    refresh_policy_cache(db)          # 신규: 전체 조회 → cached_policies upsert
    run_recommendation_batch_for_all_users(db)
```

`refresh_policy_cache`는 `policy_key` 기준으로 upsert(있으면 갱신, 없으면 삽입)
하고 `refreshed_at`을 갱신한다. 서버가 처음 켜졌을 때(캐시가 비어있을 때) "정책
읽기" 탭이 빈 화면을 보여주지 않도록, **앱 시작 시(lifespan)에도 캐시가
비어있으면 한 번 즉시 채운다** (배치 재실행이 아니라 최소한의 seed).

## 2. 상태 배지 계산 (요청 시점 계산, 저장 안 함)

`apply_end_ymd`, `apply_start_ymd`(둘 다 `YYYYMMDD` 문자열 또는 None)와 오늘
날짜(KST)를 비교:

| 조건 | 상태 |
|---|---|
| `apply_end_ymd`가 없음(상시/연중) | 🟢 신청가능 |
| 오늘 < `apply_start_ymd` | ⚪ 신청예정 |
| `apply_start_ymd` ≤ 오늘 ≤ `apply_end_ymd`, 종료까지 7일 초과 | 🟢 신청가능 |
| `apply_start_ymd` ≤ 오늘 ≤ `apply_end_ymd`, 종료까지 7일 이내 | 🟡 마감임박 |
| 오늘 > `apply_end_ymd` | 🔴 마감 |

이 로직은 순수 함수로 만들어(`compute_policy_status(apply_start_ymd, apply_end_ymd, today)`)
백엔드에서 계산해 프론트에 상태 문자열/이모지로 내려준다.

## 3. 백엔드 API (신규, `policy_matcher` 라우터에 추가)

### `GET /policy_matcher/browse`
쿼리 파라미터: `category`(옵션, `large_category` 정확히 일치), `page`(기본 1),
`page_size`(기본 20), `include_closed`(기본 false — true면 🔴마감 포함).

응답:
```json
{
  "items": [
    {
      "policy_name": "...",
      "benefit_description": "...",
      "application_period": "...",
      "reference_url": "...",
      "large_category": "주거",
      "status": "마감임박",
      "status_emoji": "🟡"
    }
  ],
  "total": 123,
  "page": 1,
  "page_size": 20
}
```
기본적으로 🔴마감 정책은 목록에서 제외한다(요구사항 "지난 정책 제외").

### `GET /policy_matcher/categories`
캐시에 실제 존재하는 `large_category`별 건수(마감 제외 기준)를 반환:
```json
{"categories": [{"name": "주거", "count": 340}, {"name": "교육・직업훈련", "count": 512}, ...]}
```
프론트가 카테고리 칩을 하드코딩하지 않고 이 응답으로 렌더링한다.

이 두 엔드포인트는 인증 불필요 여부를 확인해야 한다 — 다른 `policy_matcher`
엔드포인트는 전부 `get_current_user`로 보호되어 있으므로, 일관성을 위해
**로그인 필요**로 통일한다(비로그인 랜딩 페이지 용도가 아니므로 굳이 예외를
둘 이유가 없다).

## 4. 추천 알림 배지

### 4.1 DB 변경
`PolicyRecommendation`에 `is_read: Boolean, default=False, nullable=False` 추가.

### 4.2 API
- `GET /policy_matcher/recommendations` 응답에 이미 있는 각 항목에 `is_read`
  필드 포함, 그리고 `unread_count`를 응답 최상위에 함께 반환(프론트가 배지
  숫자를 별도 요청 없이 바로 쓸 수 있도록):
  ```json
  {"recommendations": [...], "unread_count": 3}
  ```
- `PATCH /policy_matcher/recommendations/{id}/read` — 해당 항목 `is_read=True`로
  변경, 다른 유저의 추천 항목은 404 처리(현재 유저 소유 검증).

### 4.3 프론트
- `app/(app)/layout.tsx`의 `TABS` 렌더링에서 "추천" 탭 옆에 `unread_count > 0`이면
  작은 배지(숫자)를 표시. 배지 숫자는 레이아웃이 마운트될 때 가벼운 폴링(예:
  60초 간격) 또는 페이지 포커스 시 갱신 — 실시간 웹소켓까지는 이번 스코프 아님.
- `app/(app)/recommendations/page.tsx`: 각 항목 클릭 시(또는 "자세히" 버튼)
  `PATCH .../read` 호출 후 그 항목만 로컬 상태에서 읽음 처리, 배지 숫자 갱신.

## 5. 프론트 — 정책 읽기 탭 (신규)

- 새 경로 `app/(app)/browse/page.tsx`, `layout.tsx`의 `TABS`에 6번째 탭으로 추가
  (아이콘 예: 📖, 라벨 "정책 읽기").
- 상단에 카테고리 칩 목록(`/policy_matcher/categories` 응답 기반, "전체" 칩
  포함), 칩 클릭 시 `/policy_matcher/browse?category=...`로 재조회.
- 카드형 리스트: 정책명, 상태 배지(🟢/🟡/⚪/🔴 + 텍스트), 신청기간 텍스트,
  대분류, 외부 링크.
- 하단 페이지네이션(이전/다음 또는 페이지 번호).
- `lib/api.ts`에 `getPolicyCategories`, `browsePolicies`, `patchRecommendationRead`
  추가, `Recommendation` 타입에 `is_read` 추가.

## 6. 테스트 계획

- `compute_policy_status` 순수 함수 단위 테스트 (5가지 경계 케이스: 상시, 예정,
  임박 경계 7일/8일, 마감).
- `refresh_policy_cache`: upsert 동작(신규 삽입 / 기존 갱신), `fetch_all_policies`
  mock.
- `/policy_matcher/browse`: 카테고리 필터, 마감 기본 제외, `include_closed=true`,
  페이지네이션.
- `/policy_matcher/categories`: 마감 제외 카운트.
- 추천 배지: `unread_count` 계산, `PATCH .../read`가 본인 소유만 수정 가능(다른
  유저 항목 404).
- 기존 policy_matcher/recommender 테스트는 `RawYouthPolicy` 확장에 따른 회귀가
  없는지 전체 스위트로 확인.

## Global Constraints

- 기존 `RawYouthPolicy`를 쓰는 `matching.py`/`tool.py`/`recommender.py`를 깨지 않는다.
- 새 배치 스케줄을 추가하지 않는다 — 기존 새벽 3시 잡 안에서 순서만 확장한다.
- `policy_matcher` 라우터의 기존 인증 패턴(`get_current_user`)을 새 엔드포인트에도
  동일하게 적용한다.
- 온통청년 API 실호출이 필요한 부분은 mock 테스트만으로 끝내지 말고, 가능하면
  실제 키로 라이브 검증한다(이 세션에서 이미 확립된 관행).
