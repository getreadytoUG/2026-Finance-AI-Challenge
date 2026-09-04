# CLAUDE.md

Trinity 프로젝트에서 작업하는 Claude(또는 다른 엔지니어)를 위한 컨텍스트 문서.
서비스 기획 전체는 [기획서.md](./기획서.md) 참고. 이 문서는 "기획 대비 지금 코드가
실제로 어디까지 와 있는지"와 "어떻게 작업해야 하는지"를 다룬다.

## 작업 방식 — git은 절대 건드리지 않는다

이 저장소에서는 **`git add`, `git commit`, `git push`를 포함해 git 상태를 바꾸는
어떤 명령도 실행하지 않는다.** 코드/문서 수정은 파일만 고쳐서 워킹 트리에 그대로
남겨두고, 커밋 여부와 시점은 전적으로 사용자가 직접 결정한다. `git status`,
`git diff`, `git log` 같은 읽기 전용 조회는 괜찮다.

이 규칙은 **서브에이전트에게도 동일하게 적용된다** — subagent-driven-development
같은 워크플로우로 여러 태스크를 구현할 때도, 각 태스크의 구현을 커밋하지 말고
수정된 상태로 남겨두도록 dispatch 지시문에 명시할 것. (이전에는 태스크마다
커밋하는 SDD 관행을 그대로 진행했는데, 사용자가 그것도 하지 말라고 명시적으로
정정했다 — 2026-08-24.) 

## 한 줄 요약

청년/신혼부부에게 정책을 추천하고, 그 정책을 저축 플랜과 연결하는 AI 금융·정책
통합 서비스. 기획서 기준 핵심 대분류는 **정책 | 저축플랜** 두 개.

## 지금 코드가 기획과 다른 점 (중요)

기획서의 대분류(정책 / 저축&목돈)와 달리, 현재 코드는 4개의 독립된 "Tool"이
평행하게 나열된 구조다:

- `policy_matcher` — 정책 비교 (기획서 5장에 해당, 실 API 연동 완료)
- `savings_planner` — 저축 플랜 (기획서 6장, 아직 placeholder 로직)
- `subscription_report` — 구독료 리포트 (기획서 8장, placeholder)
- `card_spending_report` — 카드소비 리포트 (기획서 9장, placeholder — 기획서에서는
  "보류" 항목이었는데 스캐폴딩은 이미 되어 있다)

기획서대로 "정책 | 저축플랜" 2대분류 + 하위 기능 구조로 재편하는 작업은
[PLAN.md](./PLAN.md)에서 진행 상황을 추적한다. **아직 코드 재편은 시작 전이고,
지금은 4개 탭이 나란히 있는 상태 그대로다.**

## 아키텍처

모노레포: `backend/`(FastAPI) + `frontend/`(Next.js App Router).

### backend
- `app/tools/` — Tool 확장 프레임워크. `ToolSpec`(이름/설명/입출력 스키마/실행 함수),
  `ToolRegistry`, `POST /tools/{name}` 범용 엔드포인트로 등록된 기능을 이름으로 호출.
- `app/features/<기능이름>/` — 실제 기능 하나당 폴더 하나. `schemas.py`(입출력
  pydantic 모델) + `tool.py`(`run(input, ctx)` + `TOOL_SPEC`). 새 기능 추가 시 이
  구조를 복제하고 `features/__init__.py`에 한 줄만 등록하면 된다.
- `app/auth/` — JWT 회원가입/로그인, 사용자 프로필(나이/혼인여부/소득/지역).
- `app/features/policy_matcher/` — 유일하게 실 데이터를 쓰는 기능. 온통청년
  (청년정책통합정보시스템) Open API(`/go/ythip/getPlcy`, JSON) 실호출. 매일 새벽
  3시 APScheduler 배치(`recommender.py`)가 유저 프로필 기준으로 신규 매칭 정책을
  찾아 "추천" 탭에 쌓는다.
- 지금 "Tool 호출" 구조는 **LLM이 오케스트레이션하는 Agent가 아니라, 프론트가
  폼 입력을 받아 해당 엔드포인트를 직접 호출하는 REST 방식**이다. LLM Provider
  추상화 코드(`app/llm/`)는 만들어져 있지만 현재 미사용(dormant) — 예전에 있던
  `/chat` 챗봇 오케스트레이션 엔드포인트는 제거된 상태다.

### frontend
- `app/login`, `app/signup` — 인증 화면 (카드형 UI, `PasswordField` 컴포넌트로
  비밀번호 표시/숨김 토글 공용화).
- `app/(app)/` — 로그인 후 화면. 공통 레이아웃(`layout.tsx`)이 탭 네비게이션 +
  인증 가드를 담당. 탭 5개: 정책비교/저축플랜/구독료 리포트/카드소비 리포트/추천.
- `lib/api.ts` — 백엔드 API 호출 함수 모음.

### 실행/배포
로컬 실행, 테스트, Cloudtype 배포 절차는 전부 루트 [README.md](../README.md)에
문서화되어 있다. 여기서 중복 설명하지 않는다.

## 알려진 제약 (기획서 대비, 또는 이번 구현에서 발견된 것)

- **지역 매칭은 시/도 단위 근사치**: zipCd(법정동코드) 콤마목록의 앞 2자리를
  17개 시/도 이름과 매핑하는 방식이다. "서울 강남구"처럼 구/군까지 지정한 입력은
  매핑 테이블에 없으면 필터링하지 않고 그냥 통과시킨다(안전 쪽으로 fail-open).
  (혼인상태 필터는 2026-09-03에 해결됨 — 아래 "정책 코드값(온통청년 공통코드)" 참고.)
- **Cloudtype 자동배포는 GitHub Actions로 걸려있음**: `main` 브랜치에 push되면
  `.github/workflows/deploy-{backend,frontend}.yml`이 각각 `backend/**`,
  `frontend/**` 변경을 감지해 Cloudtype으로 자동 배포한다(경로 트리거이므로 백엔드만
  고치면 프론트는 재배포 안 되고 그 반대도 마찬가지). 수동 재배포는 필요 없다.
- **SQLite는 재배포 시 초기화**: Cloudtype 컨테이너가 재시작되면 `app.db`가
  날아간다. 영구 저장이 필요하면 별도 볼륨 연결이 필요하다 (README 참고).
- **정책 DB 자체가 없음**: 기획서 12장이 말하는 "정책 DB"(자체 캐싱/정제된
  정책 테이블)는 없고, 매 요청마다 온통청년 API를 실시간 호출한다. 페이지당
  100건만 가져오므로(전체 약 2,700여 건) 검색/카테고리 필터링 없이는 일부만 보인다.
- **`savings_simulator`(저축플랜의 정책연계 시뮬레이터)는 2026-09-03에 실제 고시
  수치로 교체됨** — 원래 md_files/UPGRADE.md 설계대로 전부 하드코딩된 예시
  수치였는데("가품이라 못 쓴다"는 사용자 지적), 청년미래적금(청년도약계좌가
  2025-12-31 신규가입 종료되며 생긴 후속상품)/청년전용 버팀목전세자금대출/
  디딤돌대출의 실제 매칭비율·금리·LTV·소득상한으로 다시 만들었다
  (`backend/app/features/savings_simulator/simulator.py` 상단 및 각 섹션 주석에
  출처). 여전히 남은 한계: (1) 시중 상품 비교 금리(`_ASSUMED_*` 상수)는 은행마다
  매일 달라 계산기 업계 관행대로 가정치를 쓴다, (2) 가구 중위소득 조건(청년미래적금
  우대형/일반형), 생애최초 주택구입자 우대(디딤돌), 소상공인 트랙은 이 앱 프로필에
  대응 필드가 없어 반영하지 않았다 — 프론트 결과 카드에 두 가지 다 명시돼 있다.
  정부 고시는 주기적으로 바뀌므로, 이 수치들도 최신 공고와 주기적으로 대조 확인이
  필요하다.
- **정책별 챗봇의 "제출 서류"/"신청 방법" 답변은 2026-09-04부터 실제 데이터
  기반**: 그 전까진 온통청년 API의 `sbmsnDcmntCn`(제출서류)/`plcyAplyMthdCn`
  (신청방법) 필드 자체를 캐시하지 않아서, 실제로 그 정보가 있는 정책(라이브
  조회 기준 2,750건 중 각각 34%/55%)도 챗봇이 "모른다"고 답할 수밖에 없었다
  (사용자가 K패스 정책에서 "필요서류가 뭐냐" 물었더니 모른다고 답한 걸 보고
  발견 — K패스 자체는 실제로 서류가 없는 정책이라 우연히 정답이었다).
  `CachedPolicy.required_documents`/`.application_method` 컬럼을 추가하고
  `policy_chat/analysis.py`의 `_policy_text()`(정책별 챗봇과 AI 분석 리포트가
  공유하는 프롬프트 빌더)에 값이 있을 때만 포함시켰다 — 값이 없는 정책(K패스
  등)은 여전히 정직하게 "정책 정보에 없다"고 답한다.

## 정책 코드값(온통청년 공통코드)

온통청년 API가 내려주는 `mrgSttsCd`(혼인상태)/`lclsfNm`(대분류) 같은 필드는 사람이
읽는 문자열이 아니라 코드값이다. 2026-09-03에 오픈API 소개 페이지의 "코드정의서
다운로드"(`https://www.youthcenter.go.kr/downloadform/API코드정보.xlsx`)에서
공식 매핑표를 확보해 `backend/app/features/policy_matcher/matching.py`의
`MARITAL_STATUS_LABELS`에 반영했다(`0055001`=기혼, `0055002`=미혼, `0055003`=
제한없음) — 그 전엔 "기혼"/"미혼" 문자열과 비교하는 죽은 코드였다. 전체 코드표는
[DB.md](./md_files/DB.md) 부록에 옮겨뒀다.

**제공기관그룹코드(`pvsnInstGroupCd`)도 캐시에 추가했다**(`institution_group_code`
컬럼, `0054001`=중앙부처/`0054002`=지자체) — `is_likely_template_region_code()`가
"지역코드에 17개 시/도가 다 나열된 레코드"를 판별할 때, 지자체가 그러면 데이터
실수(의성/서산 사례)로, 중앙부처가 그러면 정상적인 전국 상품("햇살론유스" 등)으로
구분하는 데 쓴다. 이게 없었을 땐 이 필터가 햇살론유스 같은 진짜 전국 상품까지
잘못 걸러내고 있었다(2026-09-03 사용자 발견).

**"매칭에 안 쓰는" 관련 필드가 더 있다**: 같은 코드정의서에 `sbizCd`(정책특화요건,
`0014005`=장애인 포함)/`jobCd`/`schoolCd`/`plcyMajorCd`/`earnCndSeCd`/
`aplyPrdSeCd`/`bizPrdSeCd`도 있는데, `youth_center_client.py`가 아직 이 필드들을
캐시에 담지 않는다 — 특히 `sbizCd`의 `0014005`는 지금 정책명 키워드로만 판별하는
`is_disability_targeted_policy()`를 실제 구조화 데이터로 보완할 수 있는 후보다
(`PLAN.md` #2 참고, 라이브 조회 기준 5~6건뿐이라 키워드 판별을 대체하기보다
OR로 보완하는 쪽이 안전해 보인다).

**admin "코드값" 탭**(`/admin/code-values`, `GET /admin/policies/code-values`)에서
지금 캐시에 실제로 쌓인 원본 코드값(혼인상태/지역코드 접두사/대분류/중분류)을
매핑표와 대조해 확인할 수 있다 — 별도 테이블 없이 `cached_policies`를 매 요청마다
그대로 집계하므로 배치가 갱신될 때마다 자동으로 최신 상태다. 온통청년이 새 코드를
추가하거나(예: 광주·전남 통합 지역코드 `12`) 대분류 체계를 바꾸면 이 화면에
"매핑 안 됨"/"새 태그"로 바로 나타난다.

**중복 로직 통합**: `policy_matcher/matching.py`의 `is_eligible()`과
`policy_chat/tool.py`의 `_matches()`가 나이/소득/혼인상태 조건을 각자 복붙해서
갖고 있었다(2026-09-03 전) — `age_matches()`/`income_matches()`/
`is_married_only_policy()`/`is_unmarried_only_policy()`로 `matching.py`에 합쳐서
두 곳이 항상 같은 로직을 쓰게 했다. 이 조건들을 손볼 땐 두 파일 다 살펴볼 필요 없이
`matching.py`만 고치면 된다.

**위 통합이 불완전했던 부분(2026-09-04 발견·수정)**: 사용자 지적("정책달력
맞춤검색결과랑 한눈에보기 신청가능 정책 개수가 왜 달라?") — `matching.py`의
`TARGETING_RULES`에 있는 재학생/재직자/자영업자/미취업자/중소기업재직 "전용"
정책 자동 제외가 `is_eligible()`(한눈에보기, `/tools/policy_matcher`)에만 적용되고
`_matches()`(정책달력 "맞춤 검색 결과", `/policy_chat/ai_search/results`)에는
빠져 있었다 — `PolicyChatSearchInput`에 애초에 `occupation`/`is_sme_employee`
필드가 없어서, 프론트가 `occupation`을 쿼리로 보내도(`fetchAiSearchResults`)
백엔드가 받는 파라미터 자체가 없어 조용히 무시됐다. `PolicyChatSearchInput`에 두
필드를 추가하고 `_matches()`에 `is_student_only_policy()` 등 동일한 predicate로
필터를 걸고, `get_ai_search_results`/`_profile_default_filters`(router.py)가
`User.occupation`/`is_sme_employee`를 채워 넣게 고쳤다. 장애인/보훈대상자
(`disability_target`/`veteran_target`)는 이 두 화면이 의도적으로 다르게 동작한다
— "한눈에보기"는 프로필 기준 fail-closed로 자동 제외하지만, "정책달력"은 명시적
opt-in 열람 필터라 켜지 않으면 기본적으로 다 보여준다(그대로 둠).

## 코딩 컨벤션

- 테스트: `pytest`(backend). 기능 추가/수정 시 반드시 함께 작성하고 전체 스위트
  통과를 확인한다.
- 기능 폴더 구조를 그대로 따른다 (`schemas.py` + `tool.py` + `TOOL_SPEC`).
- 실제 외부 API를 건드리는 변경은 mock 테스트만으로 끝내지 말고, 가능하면 실제
  키로 라이브 호출까지 검증한다 (이번 온통청년 endpoint 교체 때 실제로 그렇게 해서
  숨어있던 파싱 버그 2개를 더 찾았다).
