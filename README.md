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
- 아직 프론트엔드에 회원가입 화면이 없으므로, 최초 계정은 `/docs`(Swagger) 또는 curl로 `POST /auth/signup`을 호출해 만들어야 합니다.
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

### `backend/app/features/` — 실제 기능들 (현재는 placeholder 로직만 있음)
각 폴더가 기능 하나입니다. **새 기능을 추가할 때는 이 폴더 구조를 그대로 복제**하고, `features/__init__.py`에 한 줄만 등록하면 됩니다 — `tools/` 코어나 `main.py`는 건드릴 필요가 없습니다.

- `policy_matcher/` — 청년/신혼부부 정책 비교, 가/불가 및 우대금리 판단
- `savings_planner/` — 월급·목표금액 기반 저축/적금 자동 배분
- `subscription_report/` — 구독료 사용 리포트
- `card_spending_report/` — 카드 소비 카테고리별 리포트

각 폴더 안에는 `schemas.py`(입출력 pydantic 모델)와 `tool.py`(`run(input, ctx)` 함수 + 이를 감싸는 `TOOL_SPEC`)가 있습니다. `tool.py`의 `run()` 함수 하나가 요청하신 "func_1" 형태이며, 이 안에서 판단 로직을 처리합니다. 지금은 전부 고정된 샘플 데이터를 반환하며, 실제 공공데이터/은행 API 연동은 아직 구현되지 않았습니다.

`features/__init__.py` — 위 4개 `TOOL_SPEC`을 `ToolRegistry`에 등록하는 곳. 새 기능 추가 시 여기에 import 한 줄 + 리스트 한 줄만 추가합니다.

### `backend/app/llm/` — LLM Provider 추상화 (현재 미사용, 재활용 대기)
- `base.py` — `Message`, `LLMResponse`, `LLMProvider` 인터페이스 (Claude/GPT 공통 추상화)
- `claude_provider.py` / `openai_provider.py` — 각각 Anthropic/OpenAI SDK로 실제 호출
- `factory.py` — `.env`의 `LLM_PROVIDER` 값에 따라 사용할 provider를 선택

원래는 `POST /chat`이 이 provider들로 LLM에게 Tool 호출을 맡기는 챗봇형 오케스트레이션이었지만, "실제 기능을 폼 입력으로 바로 실행"하는 방향으로 바뀌면서 `/chat` 엔드포인트는 제거했습니다. LLM 연동 코드 자체는 남겨뒀으니, 이후 특정 기능(`policy_matcher` 등) 내부에서 판단 보조용으로 재사용할 수 있습니다.

### `backend/app/shared/` — 기능 간 공유 데이터
- `models.py` — `Account`(계좌), `Transaction`(거래내역) — 여러 기능이 공통으로 참조할 테이블

### `backend/app/main.py`
FastAPI 앱 진입점. 위 라우터들(`auth`, `tools`)을 전부 등록하고 CORS·DB 테이블 생성을 처리합니다.

### `backend/tests/`
`backend/app/` 각 모듈에 대응하는 테스트 (auth, tools, features, llm 등). 총 37개, `pytest -v`로 전체 실행됩니다.

### `frontend/`
- `app/login/page.tsx` — 로그인 화면 (로그인 성공 시 JWT를 `localStorage`에 저장, 로그인 후 `/policy`로 이동)
- `app/(app)/layout.tsx` — 로그인 후 화면 공통 레이아웃: 탭 네비게이션 바 + 인증 가드(토큰 없으면 `/login`으로 리다이렉트) + 로그아웃 버튼
- `app/(app)/policy/page.tsx` — 정책비교 폼 → `POST /tools/policy_matcher`
- `app/(app)/savings/page.tsx` — 저축플랜 폼 → `POST /tools/savings_planner`
- `app/(app)/subscriptions/page.tsx` — 구독료 리포트 폼 → `POST /tools/subscription_report`
- `app/(app)/cards/page.tsx` — 카드소비 리포트 폼 → `POST /tools/card_spending_report`
- `app/page.tsx` — 루트 접속 시 로그인 여부에 따라 `/policy` 또는 `/login`으로 리다이렉트
- `lib/api.ts` — 백엔드 API 호출 함수: `login`(로그인), `callTool`(범용 `/tools/{name}` 호출 — 4개 탭이 전부 이 함수를 공유)

### `docs/superpowers/`
- `specs/` — 설계 문서 (플랫폼 아키텍처 결정 사항)
- `plans/` — 구현 계획 문서 (태스크별 작업 내역)

## 현재 범위 밖 (다음 단계)

- 4개 기능의 실제 공공데이터·은행 API 연동, 실제 판단/배분 알고리즘
- apibazzar.com에 기능을 block으로 등록하는 연동
- 프론트엔드 회원가입 화면
