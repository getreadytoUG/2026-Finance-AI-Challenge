# 2026 금융 AI 해커톤 — 플랫폼 스캐폴딩 & Tool 확장 아키텍처 설계

## 배경 및 목표

"청년 및 신혼부부를 위한 다각도 AI 웹서비스"를 만든다. 초기 기획 기능은 4가지:

1. **정책 매칭/비교**: 현재 상황(자동 입력 또는 수동 입력) 기반으로 청년/신혼부부 정책을 비교, 가/불가 판정, 우대금리 판단, 관련 웹사이트 링크 제공
2. **저축 플래너**: 월급 + 목표금액 입력 시 입출금 통장과 연계해 저축/적금 배분을 AI가 유동적으로 설계
3. **구독료 리포트**: 전체 구독 서비스 파악, 지난달 사용 내역 기반 리포트 작성
4. **카드 소비 리포트**: 카드 사용 내역 기반 카테고리별 소비 분석 리포트 작성

이 기능들은 앞으로 더 늘어날 것이 확실하므로, **기능을 추가할 때 플랫폼 코어를 건드리지 않고 폴더 하나만 추가하면 되는 구조**가 이번 설계의 핵심 목표다. 각 기능은 "하나의 진입 함수 안에서 필요한 처리를 다 수행하고 결과를 반환"하는 형태(`func_1`, `func_2` ... 패턴)로 구현하며, 이 함수를 LLM의 tool-calling 대상이자 REST API 엔드포인트로도 재사용한다.

향후 apibazzar.com(외부 API 마켓플레이스)에 각 기능을 "block"으로 등록하는 것도 염두에 두지만, 현재 공개 문서상 등록 절차가 확인되지 않아 이번 설계 범위에서는 제외한다. 대신 각 기능의 스펙(설명, 입출력 스키마)을 한 곳에 선언해두어, 추후 등록 시 이 스펙을 재사용할 수 있게 한다.

## 범위

이번 스펙은 **플랫폼 스캐폴딩과 Tool 확장 프레임워크**를 대상으로 한다. 4개 기능의 상세 비즈니스 로직(공공데이터 API 구체 연동, 우대금리 판단 알고리즘 등)은 이 스펙에 포함하지 않고, 각 기능 폴더 안에 자리(placeholder)만 만든 뒤 이후 별도로 채워나간다.

## 결정된 제약사항

- 백엔드: Python + FastAPI
- 프론트엔드: Next.js (모노레포, `frontend/`)
- DB: SQLite + SQLAlchemy (해커톤 규모에 적합, 추후 Postgres 마이그레이션 용이)
- LLM: Provider 추상화로 시작 (Claude, GPT 동시 지원)
- 인증: JWT 기반 간단한 회원가입/로그인
- 데이터: 실제 공공데이터(오픈API 등) 연동까지 이번 설계에 포함 (구체 API는 기능별 스펙에서 결정)

## 아키텍처

### 1. 모노레포 구조

```
2026-Finance-AI-Challenge/
├── backend/
│   ├── app/
│   │   ├── main.py                     # FastAPI 앱 진입점, 라우터 등록
│   │   ├── core/
│   │   │   ├── config.py               # 환경변수/설정 (pydantic-settings)
│   │   │   ├── security.py             # JWT 발급/검증, 비밀번호 해싱
│   │   │   └── db.py                   # SQLAlchemy engine/session
│   │   ├── auth/
│   │   │   ├── router.py               # /auth/signup, /auth/login
│   │   │   ├── models.py               # User
│   │   │   ├── schemas.py
│   │   │   └── service.py
│   │   ├── llm/
│   │   │   ├── base.py                 # LLMProvider Protocol
│   │   │   ├── claude_provider.py
│   │   │   ├── openai_provider.py
│   │   │   ├── factory.py              # 환경변수로 provider 선택
│   │   │   └── chat_router.py          # POST /chat — 오케스트레이션
│   │   ├── tools/                      # Tool 확장 프레임워크 (코어, 기능 추가 시 수정 불필요)
│   │   │   ├── base.py                 # ToolSpec, ToolContext 정의
│   │   │   ├── registry.py             # register_tool(), ToolRegistry, discover()
│   │   │   └── errors.py               # ToolExecutionError
│   │   ├── features/                   # 기능별 폴더 — 새 기능 추가 시 여기에만 추가
│   │   │   ├── policy_matcher/
│   │   │   │   ├── tool.py             # def run(input, ctx) -> output + TOOL_SPEC
│   │   │   │   ├── schemas.py          # pydantic input/output 모델
│   │   │   │   ├── data_sources.py     # 공공데이터 API 어댑터 (placeholder)
│   │   │   │   └── router.py           # 선택적 직접 REST 엔드포인트
│   │   │   ├── savings_planner/        # 동일 패턴
│   │   │   ├── subscription_report/    # 동일 패턴
│   │   │   └── card_spending_report/   # 동일 패턴
│   │   └── shared/
│   │       └── models.py               # Account, Transaction 등 기능 간 공유 테이블
│   ├── tests/
│   │   ├── tools/                      # registry 동작 테스트
│   │   └── features/                   # 기능별 unit test (외부 API mock)
│   ├── pyproject.toml
│   └── .env.example
├── frontend/                           # Next.js
│   └── (app/, components/, ...)
├── docs/
│   └── superpowers/specs/
└── README.md
```

### 2. Tool 확장 프레임워크

**핵심 원칙: 기능 추가는 `features/<이름>/` 폴더 하나를 새로 만드는 것으로 끝나야 하고, `tools/` 코어와 `main.py`는 수정하지 않는다.**

`app/tools/base.py`:

```python
class ToolSpec(BaseModel):
    name: str                       # 예: "policy_matcher"
    description: str                # LLM에게 보여줄 설명
    input_schema: type[BaseModel]   # pydantic 모델
    output_schema: type[BaseModel]
    entrypoint: Callable[[BaseModel, ToolContext], BaseModel]
```

각 기능의 `tool.py`:

```python
def run(input: PolicyMatchInput, ctx: ToolContext) -> PolicyMatchOutput:
    # 데이터 조회, 비교, 판단을 이 함수 안에서 전부 처리
    ...

TOOL_SPEC = ToolSpec(
    name="policy_matcher",
    description="청년/신혼부부 정책을 비교하고 가/불가·우대금리를 판단합니다",
    input_schema=PolicyMatchInput,
    output_schema=PolicyMatchOutput,
    entrypoint=run,
)
```

`app/tools/registry.py`의 `ToolRegistry`는 `features/*/tool.py`를 스캔하여 `TOOL_SPEC`들을 수집한다(명시적 import 목록 방식 — 자동 디스커버리보다 예측 가능하고 디버깅이 쉬움). 수집된 스펙으로부터:

- **LLM tool-calling 스키마** 생성 (Claude/OpenAI 포맷 각각으로 변환하는 어댑터 포함)
- **FastAPI 라우트** 자동 등록 (`POST /tools/{name}` — 직접 호출/디버깅/향후 apibazzar 연동용)
- (향후) apibazzar block manifest 생성 근거

`ToolContext`는 요청 범위 공용 정보(로그인 사용자, DB 세션)를 담아 각 `run()`에 주입한다.

### 3. LLM Provider 추상화

```python
# app/llm/base.py
class LLMProvider(Protocol):
    def chat(self, messages: list[Message], tools: list[ToolSpec]) -> LLMResponse: ...
```

`ClaudeProvider`/`OpenAIProvider`가 각자의 tool-calling 포맷으로 변환/파싱하는 세부사항을 캡슐화한다. `factory.get_provider()`가 환경변수(`LLM_PROVIDER=claude|openai`)로 인스턴스를 반환하고, `chat_router.py`는 어떤 provider인지 몰라도 동작한다.

### 4. 요청 흐름

1. 프론트 채팅 UI → `POST /chat` (JWT 인증 필요)
2. `chat_router`가 로그인 사용자로 `ToolContext` 구성, `ToolRegistry`의 전체 스펙을 provider에 전달
3. LLM이 특정 tool 호출을 결정 → `ToolRegistry.execute(name, args, ctx)`가 해당 `run()` 실행
4. 실행 결과를 LLM에 다시 전달 → 자연어 응답/리포트 생성 → 프론트에 반환
5. 필요 시 프론트는 결과에 포함된 구조화 데이터(표, 링크 등)를 별도 UI로 렌더링

### 5. 인증 & 공통 데이터 모델

- JWT 기반 회원가입/로그인 (`auth/`)
- `shared/models.py`: `User`(auth에서 참조), `Account`(입출금 통장), `Transaction`(카드/이체 내역) — 여러 기능이 공유
- 각 기능 고유 데이터(예: 구독 목록)는 해당 `features/<이름>/` 안에 모델을 두어 결합도를 낮춘다

### 6. 에러 처리

- 외부 공공데이터 API 실패 시 재시도(제한된 횟수) 후 데모용 캐시/샘플 데이터로 폴백 — 발표 중 외부 API 장애로 데모가 죽는 것을 방지
- `run()` 내부 예외는 `ToolExecutionError`로 감싸 `ToolRegistry.execute()`에서 일괄 처리, LLM에는 사람이 이해할 수 있는 에러 메시지로 전달

### 7. 테스트

- 각 `run()`은 순수 함수(입출력 pydantic 모델)이므로 외부 API를 mock으로 대체해 pytest 유닛테스트 가능
- `tools/registry.py`는 "스펙 등록 → LLM 스키마 변환 → 실행" 전체 경로에 대한 자체 테스트를 가진다

## 이번 스캐폴딩에 포함하는 것 / 포함하지 않는 것

**포함:**
- 위 폴더 구조 전체 생성
- `tools/` 프레임워크 실제 구현 (ToolSpec, Registry, 등록/실행/LLM 스키마 변환)
- `llm/` provider 추상화 실제 구현 (Claude, OpenAI 두 provider)
- `auth/` 회원가입/로그인 실제 구현
- 4개 `features/*/` 폴더 — `TOOL_SPEC`과 입출력 스키마, `run()`은 정의하되 **내부 로직은 placeholder**(고정된 샘플 응답 반환)
- `shared/` 모델 정의
- Next.js 프론트엔드 기본 골격 (채팅 UI 1페이지)
- 최소 테스트 (registry 동작, auth 플로우)

**포함하지 않음 (다음 단계):**
- 각 기능의 실제 공공데이터/은행 API 연동
- 우대금리 판단, 저축 배분 알고리즘 등 실제 비즈니스 로직
- apibazzar.com 등록 연동
- 배포 설정
