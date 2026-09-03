# 2026-Finance-AI-Challenge

청년 및 신혼부부를 위한 다각도 AI 금융 웹서비스 — 2026 금융 AI 해커톤

## 실행 방법

### 1. 백엔드 (FastAPI)

```bash
cd backend
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # Windows
# source .venv/bin/activate && pip install -r requirements.txt   # macOS/Linux

cp .env.example .env
# .env를 열어 JWT_SECRET, ANTHROPIC_API_KEY 또는 OPENAI_API_KEY를 채워주세요
# (LLM_PROVIDER=claude 이면 ANTHROPIC_API_KEY, =openai 이면 OPENAI_API_KEY 필요)

.venv/Scripts/uvicorn app.main:app --reload
```

- 서버: http://localhost:8000
- API 문서(Swagger): http://localhost:8000/docs

### 2. 프론트엔드 (Next.js)

```bash
cd frontend
npm install
npm run dev
```

- http://localhost:3000 접속 시 로그인 여부에 따라 `/login` 또는 `/policy`로 리다이렉트됩니다.
- 로그인 화면의 "회원가입" 링크로 계정을 만들 수 있습니다 (`/signup`, 이메일·비밀번호만 입력하면 가입과 동시에 자동 로그인됩니다).
- 로그인하면 4개 기능 탭(정책비교/저축플랜/구독료 리포트/카드소비 리포트)이 있는 화면으로 이동합니다. 각 탭은 채팅이 아니라 **폼 입력 → 결과 표시** 형태입니다.

### 3. 테스트 (백엔드)

```bash
cd backend
.venv/Scripts/pytest -v
```

## 프로젝트 구조

모노레포: `backend/`(FastAPI) + `frontend/`(Next.js). 기능별로 폴더를 나눠 관리합니다.

```
backend/app/
├── core/        공통 설정 (config, db, security)
├── auth/        회원가입/로그인 (JWT)
├── tools/       Tool 확장 프레임워크 (핵심)
├── features/    실제 기능들 (각 폴더 = 기능 하나)
├── llm/         LLM 연동 (Claude/GPT) — 현재 REST 화면에서는 미사용, 추후 재활용 가능
├── shared/      기능 간 공유 데이터 모델
└── main.py      앱 진입점, 라우터 등록

frontend/
├── app/login/       로그인 화면
├── app/signup/      회원가입 화면
├── app/(app)/       로그인 후 화면 (공통 탭 네비게이션 + 인증 가드)
│   ├── policy/          정책비교
│   ├── savings/         저축플랜
│   ├── subscriptions/   구독료 리포트
│   └── cards/           카드소비 리포트
└── lib/api.ts       백엔드 API 호출 함수
```

### `backend/app/core/` — 공통 설정
- `config.py` — 환경변수 기반 설정(`Settings`): DB 경로, JWT 시크릿, LLM API 키/모델명 등
- `db.py` — SQLAlchemy engine/session, `Base`
- `security.py` — 비밀번호 해싱(bcrypt), JWT 발급/검증

### `backend/app/auth/` — 회원가입/로그인
- `models.py` — `User` 테이블
- `schemas.py` — 요청/응답 pydantic 모델
- `service.py` — 회원가입/인증 로직
- `router.py` — `POST /auth/signup`, `POST /auth/login`, `GET /auth/me`, 그리고 다른 라우터들이 재사용하는 `get_current_user` 인증 의존성

### `backend/app/tools/` — Tool 확장 프레임워크 (기능 추가의 핵심)
- `base.py` — `ToolSpec`(기능 이름/설명/입출력 스키마/실행 함수), `ToolContext`(실행 시 필요한 유저/DB 정보)
- `registry.py` — `ToolRegistry`: 기능 등록·조회·실행을 담당하는 중앙 레지스트리
- `router.py` — `POST /tools/{name}`: 등록된 아무 기능이나 이름으로 직접 호출 (디버깅/apibazzar 연동용)
- `errors.py` — `ToolExecutionError`

### `backend/app/features/` — 실제 기능들 (policy_matcher는 실제 데이터 연동, 나머지 3개는 placeholder 로직)
각 폴더가 기능 하나입니다. **새 기능을 추가할 때는 이 폴더 구조를 그대로 복제**하고, `features/__init__.py`에 한 줄만 등록하면 됩니다 — `tools/` 코어나 `main.py`는 건드릴 필요가 없습니다.

- `policy_matcher/` — 청년/신혼부부 정책 비교, 온통청년 API 기반 가/불가 판단
- `savings_planner/` — 월급·목표금액 기반 저축/적금 자동 배분
- `subscription_report/` — 구독료 사용 리포트
- `card_spending_report/` — 카드 소비 카테고리별 리포트

각 폴더 안에는 `schemas.py`(입출력 pydantic 모델)와 `tool.py`(`run(input, ctx)` 함수 + 이를 감싸는 `TOOL_SPEC`)가 있습니다. `tool.py`의 `run()` 함수 하나가 요청하신 "func_1" 형태이며, 이 안에서 판단 로직을 처리합니다. policy_matcher는 온통청년 API를 실제로 호출하고, 나머지 3개는 아직 고정된 샘플 데이터를 반환합니다.

`features/__init__.py` — 위 4개 `TOOL_SPEC`을 `ToolRegistry`에 등록하는 곳. 새 기능 추가 시 여기에 import 한 줄 + 리스트 한 줄만 추가합니다.

### `backend/app/llm/` — LLM Provider 추상화 (현재 미사용, 재활용 대기)
- `base.py` — `Message`, `LLMResponse`, `LLMProvider` 인터페이스 (Claude/GPT 공통 추상화)
- `claude_provider.py` / `openai_provider.py` — 각각 Anthropic/OpenAI SDK로 실제 호출
- `factory.py` — `.env`의 `LLM_PROVIDER` 값에 따라 사용할 provider를 선택

원래는 `POST /chat`이 이 provider들로 LLM에게 Tool 호출을 맡기는 챗봇형 오케스트레이션이었지만, "실제 기능을 폼 입력으로 바로 실행"하는 방향으로 바뀌면서 `/chat` 엔드포인트는 제거했습니다. LLM 연동 코드 자체는 남겨뒀으니, 이후 특정 기능(`policy_matcher` 등) 내부에서 판단 보조용으로 재사용할 수 있습니다.

### `backend/app/shared/` — 기능 간 공유 데이터
- `models.py` — `Account`(계좌), `Transaction`(거래내역) — 여러 기능이 공통으로 참조할 테이블

### `backend/app/main.py`
FastAPI 앱 진입점. 위 라우터들(`auth`, `tools`, `policy_matcher`)을 전부 등록하고 CORS·DB 테이블 생성·APScheduler(매일 새벽 3시 정책 추천 배치) 기동/종료를 처리합니다.

### `backend/tests/`
`backend/app/` 각 모듈에 대응하는 테스트 (auth, tools, features, llm 등). 총 97개, `pytest -v`로 전체 실행됩니다.

### `frontend/`
- `app/login/page.tsx` — 로그인 화면 (로그인 성공 시 JWT를 `localStorage`에 저장, 로그인 후 `/policy`로 이동)
- `app/signup/page.tsx` — 회원가입 화면 (이메일·비밀번호만 입력, 가입 성공 시 자동 로그인 후 `/policy`로 이동. 중복 이메일/이메일 형식 오류는 백엔드가 반환하는 메시지를 그대로 표시 — 프론트엔드 자체 검증은 아직 없음)
- `app/(app)/layout.tsx` — 로그인 후 화면 공통 레이아웃: 탭 네비게이션 바 + 인증 가드(토큰 없으면 `/login`으로 리다이렉트) + 로그아웃 버튼
- `app/(app)/policy/page.tsx` — 정책비교 폼 → `POST /tools/policy_matcher`
- `app/(app)/savings/page.tsx` — 저축플랜 폼 → `POST /tools/savings_planner`
- `app/(app)/subscriptions/page.tsx` — 구독료 리포트 폼 → `POST /tools/subscription_report`
- `app/(app)/cards/page.tsx` — 카드소비 리포트 폼 → `POST /tools/card_spending_report`
- `app/(app)/recommendations/page.tsx` — 맞춤 추천 (프로필 미완성 시 입력 폼, 완성 시 추천 목록 + 수동 갱신 버튼)
- `app/page.tsx` — 루트 접속 시 로그인 여부에 따라 `/policy` 또는 `/login`으로 리다이렉트
- `lib/api.ts` — 백엔드 API 호출 함수: `login`/`signup`(로그인/회원가입), `callTool`(범용 `/tools/{name}` 호출 — 정책비교/저축플랜/구독료/카드소비 탭이 공유), `getMe`/`updateProfile`/`getRecommendations`/`refreshRecommendations`(추천 탭 전용)

### `docs/superpowers/`
- `specs/` — 설계 문서 (플랫폼 아키텍처 결정 사항)
- `plans/` — 구현 계획 문서 (태스크별 작업 내역)

## 배포 (Cloudtype)

모노레포이므로 **백엔드와 프론트엔드를 각각 별도 서비스로** 배포합니다. 같은 GitHub 저장소를 두 번 연결하고, 하위 디렉토리만 다르게 지정하면 됩니다. (Cloudtype 대시보드에서 저장소를 선택한 뒤 "설정변경"에 서브 디렉토리 입력란이 있습니다.)

### 1. 백엔드 배포

1. 새 서비스 생성 → 이 저장소 선택 → 서브 디렉토리: `backend`
2. 프레임워크: **FastAPI** 템플릿 선택
3. 빌드 설정
   - Install Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app.main:app --host=0.0.0.0 --port=8000`
   - 포트: `8000`
4. 환경 변수 (Cloudtype 대시보드의 "환경 변수" 항목에 직접 입력 — `.env` 파일을 커밋해서 넣지 마세요)
   - `JWT_SECRET`: 랜덤한 긴 문자열
   - `LLM_PROVIDER`: `claude` 또는 `openai`
   - `ANTHROPIC_API_KEY` 또는 `OPENAI_API_KEY`: 위에서 고른 provider의 키
   - `CORS_ORIGINS`: 아직 프론트 URL을 모르므로 일단 비워두거나 아무 값(예: `http://localhost:3000`)으로 배포 — 2번 완료 후 업데이트합니다
   - `YOUTH_CENTER_API_KEY`: 온통청년 API 키 (발급 방법은 아래 "policy_matcher — 온통청년 API 키 발급" 절 참고)
   - (선택) 소셜 로그인을 쓰려면 `KAKAO_CLIENT_ID` / `KAKAO_CLIENT_SECRET` 와
     `KAKAO_REDIRECT_URI`(값: `<백엔드 URL>/auth/kakao/callback`),
     `FRONTEND_BASE_URL`(값: 프론트 URL)을 추가합니다. 자세한 건 아래 "소셜 로그인 설정" 절 참고.
5. 배포되면 발급되는 URL(예: `https://xxxx.cloudtype.app`)을 기억해두세요 — 프론트엔드 설정에 필요합니다.

### 2. 프론트엔드 배포

1. 같은 저장소로 새 서비스 추가 → 서브 디렉토리: `frontend`
2. 프레임워크: **Next.js** 템플릿 선택
3. 빌드 설정
   - Install Command: `npm install`
   - Build Command: `npm run build`
   - Start Command: `npm run start -- -p 3000` (또는 `next start -p 3000`)
   - 포트: `3000`
4. **Build Variables**(런타임 환경변수와 별도로, 빌드 시점에 주입되는 값 — `NEXT_PUBLIC_` 접두사 변수는 반드시 여기 설정해야 합니다)
   - `NEXT_PUBLIC_API_BASE`: 1번에서 확인한 백엔드 URL (예: `https://xxxx.cloudtype.app`)
5. 배포되면 프론트엔드 URL(예: `https://yyyy.cloudtype.app`)이 발급됩니다.

### 3. CORS 연결 마무리

백엔드 서비스로 돌아가서 환경 변수 `CORS_ORIGINS`를 방금 확인한 프론트엔드 URL로 업데이트하고 재배포하세요.
예: `CORS_ORIGINS=https://yyyy.cloudtype.app`

### 참고사항

- SQLite 파일(`backend/app.db`)은 컨테이너 파일시스템에 저장되므로 재배포/재시작 시 초기화될 수 있습니다. 데모용으로는 문제없지만, 데이터를 유지하려면 Cloudtype의 디스크(볼륨) 기능을 별도로 연결해야 합니다.
- 이 저장소를 먼저 사용해본 적이 있고 로컬에 기존 `backend/app.db` 파일이 남아있다면, `users` 테이블에 새 컬럼(age/is_married/annual_income_krw/region)이 추가되었으므로 그 파일을 삭제하고 다시 실행하세요 (`Base.metadata.create_all`은 기존 테이블에 컬럼을 추가해주지 않습니다). Cloudtype 배포는 컨테이너가 재시작되면 SQLite 파일 자체가 초기화되는 경우가 많아 보통 문제되지 않습니다.
- 배포된 프론트엔드의 `/signup`에서 계정을 만들 수 있습니다. SQLite가 재배포/재시작 시 초기화되므로, 재배포 후에는 기존 계정도 다시 만들어야 합니다.

## 소셜 로그인 설정 (카카오)

일반 이메일/비밀번호 가입과 별개로 카카오 OAuth 로그인을 지원합니다. 환경 변수를
채우지 않으면 소셜 로그인 버튼은 그대로 노출되지만 클릭 시 "설정되지 않았습니다"(503) 응답을
받습니다 — 일반 가입은 영향 없습니다.

동작 방식(백엔드 리다이렉트):

1. 프론트의 "카카오로 로그인" 버튼 → `GET <백엔드>/auth/kakao/login`
2. 백엔드가 CSRF 방어용 `state`(서명된 단기 JWT)를 붙여 프로바이더 인증 페이지로 302
3. 사용자가 동의하면 프로바이더가 `GET <백엔드>/auth/{provider}/callback?code=...&state=...` 로 리다이렉트
4. 백엔드가 `code`를 토큰으로 교환하고 프로필을 조회 → 사용자 생성/조회 → JWT 발급
5. `<프론트>/auth/callback#token=...&new=0|1` 로 리다이렉트 (토큰은 URL fragment라 서버 로그·Referer에 안 남음)
6. 프론트가 토큰을 저장하고, 프로필(나이/소득/지역/직업)이 비어 있으면 `/onboarding` 으로 보냄

계정 규칙:

- `(provider, provider_user_id)` 로 소셜 계정을 식별합니다.
- 소셜에서 받은 **검증된 이메일**이 기존 일반가입 계정과 같으면 그 계정에 자동 연동됩니다(계정 1개 유지).
- 카카오가 이메일 동의를 주지 않으면 `kakao_<id>@social.trinity.local` 자리표시자 주소로 생성되고,
  온보딩/내 정보에서 실제 이메일로 바꾸도록 안내합니다.
- 소셜 전용 계정(비밀번호 없음)은 이메일/비밀번호 로그인이 거부됩니다.

### 카카오

1. https://developers.kakao.com → 내 애플리케이션 → 애플리케이션 추가
2. 앱 키의 **REST API 키** → `KAKAO_CLIENT_ID`
3. 카카오 로그인 → 활성화 ON, **Redirect URI** 등록: `<백엔드 URL>/auth/kakao/callback`
   (로컬 개발도 쓰려면 `http://localhost:8000/auth/kakao/callback` 도 함께 등록)
4. 카카오 로그인 → 보안 → "Client Secret"을 사용으로 설정했다면 그 값을 `KAKAO_CLIENT_SECRET` 에 넣습니다(안 썼으면 비워둠)
5. (선택) 동의항목에서 "닉네임", "카카오계정(이메일)"을 설정 — 이메일은 비즈앱 전환 시에만 필수 요청 가능
6. `KAKAO_REDIRECT_URI` 를 3번에서 등록한 값과 **정확히 동일하게** 설정

### 로컬에서 테스트

`backend/.env` 에 위 값들과 함께 아래를 넣고 백엔드·프론트를 모두 로컬로 띄웁니다.

```
KAKAO_CLIENT_ID=...
KAKAO_REDIRECT_URI=http://localhost:8000/auth/kakao/callback
FRONTEND_BASE_URL=http://localhost:3000
```

## policy_matcher — 온통청년 API 키 발급

`policy_matcher` 기능은 온통청년(청년정책통합정보시스템) Open API를 실호출합니다. 키 없이는 이 기능이 동작하지 않습니다.

1. https://www.youthcenter.go.kr 에서 회원가입
2. 로그인 후 마이페이지 → OPEN API 메뉴에서 인증키 발급 신청 (관리자 승인제)
3. 승인된 키를 `backend/.env`의 `YOUTH_CENTER_API_KEY`에 입력
4. 키가 없어도 `pytest`는 통과합니다 (API 호출을 mock으로 대체) — 실제 `/tools/policy_matcher` 호출에만 키가 필요합니다

## 맞춤 추천 (매일 배치)

`policy_matcher`와 같은 온통청년 API를 사용해, 프로필을 저장한 유저에게 매일 새벽 3시(한국시간)에 새로 맞는 정책이 있는지 확인해 앱 내 "추천" 탭에 쌓아줍니다.

- 유저는 "추천" 탭에서 나이/혼인여부/소득/지역 프로필을 한 번 저장합니다 (`PUT /auth/profile`).
- 배치는 백엔드 프로세스 안에 내장된 스케줄러(APScheduler)가 실행하며, 별도 Cloudtype cron 설정은 필요 없습니다.
- **제약**: 스케줄은 프로세스 안에서만 유지됩니다 — 서버가 재시작되면(재배포, 컨테이너 재기동 등) 스케줄이 다시 등록될 뿐, 마지막 실행 시각을 기억하지 못합니다. 재시작 직후엔 다음 새벽 3시까지 배치가 돌지 않으니, 데모 중 즉시 확인하려면 "추천" 탭의 "지금 갱신" 버튼(본인 계정만 즉시 실행)을 사용하세요.
- 이 기능도 `YOUTH_CENTER_API_KEY`를 그대로 재사용합니다 — 추가 발급 필요 없음.

## 정책 읽기 탭 + 추천 알림

- **"정책 읽기" 탭**: 조건 입력 없이 전체 정책을 카테고리별로 훑어볼 수 있는 탭입니다. 신청 상태(🟢신청가능/🟡마감임박/⚪신청예정/🔴마감)를 배지로 보여주고, 마감된 정책은 기본적으로 목록에서 제외됩니다.
- **데이터 소스**: 매일 새벽 3시 배치가 온통청년 API 전체 목록을 `cached_policies` 테이블에 캐싱하고(앱 최초 기동 시 캐시가 비어있으면 즉시 한 번 채움), "정책 읽기"/"카테고리" 조회는 이 캐시에서 응답합니다 — 매 요청마다 외부 API를 호출하지 않습니다.
- **추천 알림 배지**: "추천" 탭에 미확인 정책 개수가 배지로 표시됩니다(60초 주기 폴링). 개별 항목을 클릭하면 그 항목만 읽음 처리됩니다.

## 현재 범위 밖 (다음 단계)

- policy_matcher를 제외한 3개 기능(savings_planner, subscription_report, card_spending_report)의 실제 공공데이터·은행 API 연동, 실제 판단/배분 알고리즘
- apibazzar.com에 기능을 block으로 등록하는 연동
- 회원가입 폼의 이메일 형식·중복 검사 등 프론트엔드 자체 유효성 검사 (현재는 백엔드 에러 메시지를 그대로 노출)
