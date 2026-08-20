# Platform Scaffold & Tool Extension Framework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the FastAPI + Next.js monorepo scaffold with a pluggable Tool framework, so the four hackathon features (policy matcher, savings planner, subscription report, card spending report) can each be added as a self-contained `features/<name>/` folder without touching platform core.

**Architecture:** FastAPI backend with a central `ToolRegistry` that features register a `ToolSpec` (input/output pydantic schemas + one entrypoint function) into. The registry exposes registered tools both as a generic `POST /tools/{name}` REST endpoint and as tool-calling definitions handed to an LLM provider abstraction (Claude and OpenAI). A `POST /chat` endpoint orchestrates: send user message + tool defs to the active LLM provider, execute any tool the LLM calls via the registry, loop until the LLM returns plain content. JWT auth gates all of this. Next.js frontend provides a minimal login + chat page.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy + SQLite, pydantic v2, python-jose (JWT), passlib[bcrypt], anthropic SDK, openai SDK, pytest + httpx (TestClient); Next.js (App Router) + TypeScript for frontend.

**Spec:** [docs/superpowers/specs/2026-08-20-platform-scaffold-design.md](../specs/2026-08-20-platform-scaffold-design.md)

## Global Constraints

- Backend: Python + FastAPI.
- Frontend: Next.js, same monorepo (`frontend/`).
- DB: SQLite + SQLAlchemy.
- LLM: provider abstraction from the start — both Claude and OpenAI must work behind the same `LLMProvider` interface.
- Auth: JWT-based signup/login.
- Adding a new feature must only require adding a new `app/features/<name>/` folder plus one registration line in `app/features/__init__.py` — `app/tools/` core and `app/main.py` routing must not need changes.
- Each feature's business logic lives behind one entrypoint function, e.g. `run(input, ctx) -> output`, matching the `func_1`-style pattern the user asked for.
- This plan scaffolds the 4 features with **placeholder logic only** (deterministic sample data) — real public-data API integration and real decision algorithms are out of scope for this plan.

---

## Task 1: Backend Project Init (config, DB, health check)

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/config.py`
- Create: `backend/app/core/db.py`
- Create: `backend/app/main.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Test: `backend/tests/test_health.py`

**Interfaces:**
- Produces: `app.core.config.settings` (a `Settings` instance with fields `jwt_secret: str`, `database_url: str`, `anthropic_api_key: str`, `openai_api_key: str`, `llm_provider: str`, `claude_model: str`, `openai_model: str`)
- Produces: `app.core.db.Base` (SQLAlchemy declarative base), `app.core.db.engine`, `app.core.db.get_db()` (FastAPI dependency yielding a `Session`)
- Produces: `app.main.app` (the FastAPI instance) — later tasks add routers to it
- Produces: `tests/conftest.py::client` fixture (a `TestClient` with `get_db` overridden to an isolated in-memory SQLite DB) — every later test task reuses this fixture

- [ ] **Step 1: Create the backend folder skeleton and requirements file**

Run these commands:

```bash
mkdir -p backend/app/core backend/tests
touch backend/app/__init__.py backend/app/core/__init__.py backend/tests/__init__.py
```

Create `backend/requirements.txt`:

```
fastapi
uvicorn[standard]
sqlalchemy
pydantic
pydantic-settings
email-validator
python-jose[cryptography]
passlib[bcrypt]
anthropic
openai
pytest
httpx
```

- [ ] **Step 2: Create a virtualenv and install dependencies**

```bash
cd backend
python -m venv .venv
```

Windows activation + install:

```bash
backend/.venv/Scripts/pip install -r backend/requirements.txt
```

- [ ] **Step 3: Write `app/core/config.py`**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    jwt_secret: str = "dev-secret-change-me"
    database_url: str = "sqlite:///./app.db"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    llm_provider: str = "claude"
    claude_model: str = "claude-sonnet-5"
    openai_model: str = "gpt-4o"

    model_config = {"env_file": ".env"}


settings = Settings()
```

- [ ] **Step 4: Write `app/core/db.py`**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 5: Write `app/main.py` with just a health check**

```python
from fastapi import FastAPI

app = FastAPI(title="Finance AI Hackathon")


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 6: Write the shared test fixture in `tests/conftest.py`**

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.core.db import Base, get_db
from app.main import app


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
```

- [ ] **Step 7: Write the failing test `tests/test_health.py`**

```python
def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 8: Run the test to verify it passes**

Run (from `backend/`): `.venv/Scripts/pytest tests/test_health.py -v`
Expected: PASS (Steps 3-6 already implement everything the test needs, so this confirms the scaffold works end-to-end rather than failing first — that's expected for this bootstrap task only).

- [ ] **Step 9: Commit**

```bash
git add backend/requirements.txt backend/app backend/tests
git commit -m "chore: init FastAPI backend skeleton with config, db, health check"
```

---

## Task 2: Tool Framework Core

**Files:**
- Create: `backend/app/tools/__init__.py`
- Create: `backend/app/tools/base.py`
- Create: `backend/app/tools/errors.py`
- Create: `backend/app/tools/registry.py`
- Test: `backend/tests/tools/__init__.py`
- Test: `backend/tests/tools/test_registry.py`

**Interfaces:**
- Consumes: nothing from Task 1 directly (pure module, no DB/FastAPI dependency)
- Produces: `app.tools.base.ToolSpec(name: str, description: str, input_schema: type[BaseModel], output_schema: type[BaseModel], entrypoint: Callable[[BaseModel, ToolContext], BaseModel])`
- Produces: `app.tools.base.ToolContext(user_id: int, db: Any)` (pydantic model, `arbitrary_types_allowed`)
- Produces: `app.tools.errors.ToolExecutionError(tool_name: str, message: str)`
- Produces: `app.tools.registry.ToolRegistry` with methods `register(spec: ToolSpec) -> None`, `get(name: str) -> ToolSpec`, `all() -> list[ToolSpec]`, `execute(name: str, raw_input: dict, ctx: ToolContext) -> BaseModel`
- Produces: `app.tools.registry.registry` (the process-wide `ToolRegistry()` singleton) and `app.tools.registry.get_tool_registry() -> ToolRegistry` (FastAPI-dependency-friendly accessor, overridable in tests)

- [ ] **Step 1: Create `backend/tests/tools/__init__.py` (empty) and write the failing tests in `backend/tests/tools/test_registry.py`**

```python
import pytest
from pydantic import BaseModel

from app.tools.base import ToolSpec, ToolContext
from app.tools.errors import ToolExecutionError
from app.tools.registry import ToolRegistry


class SampleInput(BaseModel):
    x: int


class SampleOutput(BaseModel):
    doubled: int


def sample_run(input: SampleInput, ctx: ToolContext) -> SampleOutput:
    return SampleOutput(doubled=input.x * 2)


def failing_run(input: SampleInput, ctx: ToolContext) -> SampleOutput:
    raise ValueError("boom")


def make_spec(entrypoint=sample_run) -> ToolSpec:
    return ToolSpec(
        name="sample_tool",
        description="doubles a number",
        input_schema=SampleInput,
        output_schema=SampleOutput,
        entrypoint=entrypoint,
    )


def test_register_and_get_returns_same_spec():
    reg = ToolRegistry()
    spec = make_spec()
    reg.register(spec)
    assert reg.get("sample_tool") is spec


def test_register_duplicate_name_raises():
    reg = ToolRegistry()
    reg.register(make_spec())
    with pytest.raises(ValueError):
        reg.register(make_spec())


def test_get_unknown_tool_raises_keyerror():
    reg = ToolRegistry()
    with pytest.raises(KeyError):
        reg.get("does_not_exist")


def test_all_returns_every_registered_spec():
    reg = ToolRegistry()
    reg.register(make_spec())
    assert [s.name for s in reg.all()] == ["sample_tool"]


def test_execute_validates_input_and_runs_entrypoint():
    reg = ToolRegistry()
    reg.register(make_spec())
    ctx = ToolContext(user_id=1, db=None)
    result = reg.execute("sample_tool", {"x": 21}, ctx)
    assert result == SampleOutput(doubled=42)


def test_execute_wraps_entrypoint_exception_in_tool_execution_error():
    reg = ToolRegistry()
    reg.register(make_spec(entrypoint=failing_run))
    ctx = ToolContext(user_id=1, db=None)
    with pytest.raises(ToolExecutionError) as exc_info:
        reg.execute("sample_tool", {"x": 1}, ctx)
    assert exc_info.value.tool_name == "sample_tool"
```

- [ ] **Step 2: Run the tests to verify they fail with import errors**

Run: `.venv/Scripts/pytest tests/tools/test_registry.py -v`
Expected: FAIL/ERROR — `ModuleNotFoundError: No module named 'app.tools'`

- [ ] **Step 3: Write `app/tools/__init__.py` (empty) and `app/tools/base.py`**

```python
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict


class ToolContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    user_id: int
    db: Any


class ToolSpec(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    description: str
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]
    entrypoint: Callable[[BaseModel, ToolContext], BaseModel]
```

- [ ] **Step 4: Write `app/tools/errors.py`**

```python
class ToolExecutionError(Exception):
    def __init__(self, tool_name: str, message: str):
        self.tool_name = tool_name
        self.message = message
        super().__init__(f"{tool_name}: {message}")
```

- [ ] **Step 5: Write `app/tools/registry.py`**

```python
from pydantic import BaseModel

from app.tools.base import ToolContext, ToolSpec
from app.tools.errors import ToolExecutionError


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        if spec.name in self._tools:
            raise ValueError(f"Tool '{spec.name}' is already registered")
        self._tools[spec.name] = spec

    def get(self, name: str) -> ToolSpec:
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not found")
        return self._tools[name]

    def all(self) -> list[ToolSpec]:
        return list(self._tools.values())

    def execute(self, name: str, raw_input: dict, ctx: ToolContext) -> BaseModel:
        spec = self.get(name)
        parsed_input = spec.input_schema.model_validate(raw_input)
        try:
            return spec.entrypoint(parsed_input, ctx)
        except Exception as e:
            raise ToolExecutionError(name, str(e)) from e


registry = ToolRegistry()


def get_tool_registry() -> ToolRegistry:
    return registry
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `.venv/Scripts/pytest tests/tools/test_registry.py -v`
Expected: PASS (6 tests)

- [ ] **Step 7: Commit**

```bash
git add backend/app/tools backend/tests/tools
git commit -m "feat: add Tool registry framework (ToolSpec, ToolContext, ToolRegistry)"
```

---

## Task 3: Auth (signup/login, JWT, current-user dependency)

**Files:**
- Create: `backend/app/auth/__init__.py`
- Create: `backend/app/auth/models.py`
- Create: `backend/app/auth/schemas.py`
- Create: `backend/app/core/security.py`
- Create: `backend/app/auth/service.py`
- Create: `backend/app/auth/router.py`
- Modify: `backend/app/main.py` — register `auth_router`, create tables on startup
- Test: `backend/tests/test_auth.py`

**Interfaces:**
- Consumes: `app.core.db.Base`, `app.core.db.get_db` (Task 1)
- Produces: `app.auth.models.User(id: int, email: str, hashed_password: str)` (SQLAlchemy model)
- Produces: `app.core.security.hash_password(password: str) -> str`, `verify_password(plain: str, hashed: str) -> bool`, `create_access_token(subject: str, expires_minutes: int = 1440) -> str`, `decode_access_token(token: str) -> str`
- Produces: `app.auth.router.get_current_user(...) -> User` (FastAPI dependency) — later tasks (Tool router, Chat router) depend on this
- Produces: routes `POST /auth/signup`, `POST /auth/login`

- [ ] **Step 1: Write the failing tests in `backend/tests/test_auth.py`**

```python
def test_signup_creates_user(client):
    response = client.post("/auth/signup", json={"email": "a@example.com", "password": "secret123"})
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "a@example.com"
    assert "id" in body
    assert "password" not in body


def test_signup_duplicate_email_returns_400(client):
    client.post("/auth/signup", json={"email": "dup@example.com", "password": "secret123"})
    response = client.post("/auth/signup", json={"email": "dup@example.com", "password": "other456"})
    assert response.status_code == 400


def test_login_with_correct_credentials_returns_token(client):
    client.post("/auth/signup", json={"email": "b@example.com", "password": "secret123"})
    response = client.post("/auth/login", json={"email": "b@example.com", "password": "secret123"})
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_with_wrong_password_returns_401(client):
    client.post("/auth/signup", json={"email": "c@example.com", "password": "secret123"})
    response = client.post("/auth/login", json={"email": "c@example.com", "password": "wrong"})
    assert response.status_code == 401


def test_protected_route_requires_token(client):
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_protected_route_returns_current_user_with_valid_token(client):
    client.post("/auth/signup", json={"email": "d@example.com", "password": "secret123"})
    login = client.post("/auth/login", json={"email": "d@example.com", "password": "secret123"})
    token = login.json()["access_token"]
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "d@example.com"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/Scripts/pytest tests/test_auth.py -v`
Expected: FAIL — `404 Not Found` (routes don't exist yet) / `ModuleNotFoundError`

- [ ] **Step 3: Write `app/auth/__init__.py` (empty) and `app/auth/models.py`**

```python
from sqlalchemy import Column, Integer, String

from app.core.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
```

- [ ] **Step 4: Write `app/auth/schemas.py`**

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


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
```

- [ ] **Step 5: Write `app/core/security.py`**

```python
from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str, expires_minutes: int = 60 * 24) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> str:
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    return payload["sub"]
```

- [ ] **Step 6: Write `app/auth/service.py`**

```python
from sqlalchemy.orm import Session

from app.auth.models import User
from app.core.security import hash_password, verify_password


def create_user(db: Session, email: str, password: str) -> User:
    existing = db.query(User).filter(User.email == email).first()
    if existing is not None:
        raise ValueError("Email already registered")
    user = User(email=email, hashed_password=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = db.query(User).filter(User.email == email).first()
    if user is None or not verify_password(password, user.hashed_password):
        return None
    return user
```

- [ ] **Step 7: Write `app/auth/router.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.auth import service
from app.auth.models import User
from app.auth.schemas import LoginRequest, SignupRequest, TokenResponse, UserOut
from app.core.db import get_db
from app.core.security import create_access_token, decode_access_token

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    try:
        user = service.create_user(db, payload.email, payload.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = service.authenticate_user(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(subject=str(user.id))
    return TokenResponse(access_token=token)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    if token is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        user_id = decode_access_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
```

- [ ] **Step 8: Wire the auth router into `app/main.py` and create tables on startup**

```python
from fastapi import FastAPI

from app.auth.models import User  # noqa: F401 — ensures table is registered on Base metadata
from app.auth.router import router as auth_router
from app.core.db import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Finance AI Hackathon")
app.include_router(auth_router, prefix="/auth", tags=["auth"])


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 9: Run the tests to verify they pass**

Run: `.venv/Scripts/pytest tests/test_auth.py -v`
Expected: PASS (6 tests)

- [ ] **Step 10: Commit**

```bash
git add backend/app/auth backend/app/core/security.py backend/app/main.py backend/tests/test_auth.py
git commit -m "feat: add JWT signup/login and get_current_user dependency"
```

---

## Task 4: Shared Data Models (Account, Transaction)

**Files:**
- Create: `backend/app/shared/__init__.py`
- Create: `backend/app/shared/models.py`
- Modify: `backend/app/main.py` — import shared models so their tables register
- Test: `backend/tests/test_shared_models.py`

**Interfaces:**
- Consumes: `app.core.db.Base`, `app.auth.models.User` (Task 3, for the foreign key)
- Produces: `app.shared.models.Account(id, user_id, account_type: str, balance_krw: int)`, `app.shared.models.Transaction(id, account_id, occurred_at: datetime, merchant: str, category: str, amount_krw: int)` — later feature tasks (savings planner, card spending report) query these

- [ ] **Step 1: Write the failing test `backend/tests/test_shared_models.py`**

```python
from app.shared.models import Account, Transaction


def test_account_and_transaction_models_are_importable_and_map_to_tables():
    assert Account.__tablename__ == "accounts"
    assert Transaction.__tablename__ == "transactions"


def test_tables_are_created_on_app_startup(client):
    # The client fixture creates all tables (via Base.metadata.create_all) against
    # an isolated in-memory DB when the app starts — if Account/Transaction weren't
    # imported anywhere before that call, their tables would silently be missing.
    # Hitting any route confirms app startup succeeded with them registered.
    response = client.get("/health")
    assert response.status_code == 200
```

Run: `.venv/Scripts/pytest tests/test_shared_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.shared'`

- [ ] **Step 2: Write `app/shared/__init__.py` (empty) and `app/shared/models.py`**

```python
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from app.core.db import Base


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    account_type = Column(String, nullable=False)  # e.g. "checking", "savings"
    balance_krw = Column(Integer, nullable=False, default=0)


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    occurred_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    merchant = Column(String, nullable=False)
    category = Column(String, nullable=False)  # e.g. "subscription", "dining", "transport"
    amount_krw = Column(Integer, nullable=False)
```

- [ ] **Step 3: Import the shared models in `app/main.py` so `Base.metadata` includes them**

In `app/main.py`, add near the other model import:

```python
from app.shared.models import Account, Transaction  # noqa: F401 — registers tables on Base metadata
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/Scripts/pytest tests/test_shared_models.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/shared backend/app/main.py backend/tests/test_shared_models.py
git commit -m "feat: add shared Account and Transaction models"
```

---

## Task 5: Feature — policy_matcher (placeholder)

**Files:**
- Create: `backend/app/features/__init__.py` (placeholder — Task 9 fills in `register_all_tools`)
- Create: `backend/app/features/policy_matcher/__init__.py`
- Create: `backend/app/features/policy_matcher/schemas.py`
- Create: `backend/app/features/policy_matcher/tool.py`
- Test: `backend/tests/features/__init__.py`
- Test: `backend/tests/features/test_policy_matcher.py`

**Interfaces:**
- Consumes: `app.tools.base.ToolSpec`, `ToolContext` (Task 2)
- Produces: `app.features.policy_matcher.tool.TOOL_SPEC` (a `ToolSpec` named `"policy_matcher"`) — Task 9 registers this
- Produces: `app.features.policy_matcher.tool.run(input: PolicyMatchInput, ctx: ToolContext) -> PolicyMatchOutput`

- [ ] **Step 1: Create empty `__init__.py` files**

```bash
mkdir -p backend/app/features/policy_matcher backend/tests/features
touch backend/app/features/__init__.py backend/app/features/policy_matcher/__init__.py backend/tests/features/__init__.py
```

- [ ] **Step 2: Write the failing test `backend/tests/features/test_policy_matcher.py`**

```python
from app.features.policy_matcher.schemas import PolicyMatchInput
from app.features.policy_matcher.tool import TOOL_SPEC, run
from app.tools.base import ToolContext


def test_tool_spec_has_expected_name_and_schemas():
    assert TOOL_SPEC.name == "policy_matcher"
    assert TOOL_SPEC.entrypoint is run


def test_run_marks_young_applicant_eligible():
    ctx = ToolContext(user_id=1, db=None)
    result = run(PolicyMatchInput(age=29, is_married=False, annual_income_krw=40_000_000, region="서울"), ctx)
    assert len(result.options) >= 1
    assert result.options[0].eligible is True


def test_run_marks_over_age_applicant_ineligible():
    ctx = ToolContext(user_id=1, db=None)
    result = run(PolicyMatchInput(age=50, is_married=False, annual_income_krw=40_000_000, region="서울"), ctx)
    assert result.options[0].eligible is False


def test_run_gives_married_applicant_better_rate():
    ctx = ToolContext(user_id=1, db=None)
    married = run(PolicyMatchInput(age=29, is_married=True, annual_income_krw=40_000_000, region="서울"), ctx)
    single = run(PolicyMatchInput(age=29, is_married=False, annual_income_krw=40_000_000, region="서울"), ctx)
    assert married.options[0].preferential_rate_percent < single.options[0].preferential_rate_percent
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `.venv/Scripts/pytest tests/features/test_policy_matcher.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.features.policy_matcher.schemas'`

- [ ] **Step 4: Write `app/features/policy_matcher/schemas.py`**

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
    preferential_rate_percent: float
    reference_url: str


class PolicyMatchOutput(BaseModel):
    options: list[PolicyOption]
```

- [ ] **Step 5: Write `app/features/policy_matcher/tool.py`**

```python
from app.features.policy_matcher.schemas import PolicyMatchInput, PolicyMatchOutput, PolicyOption
from app.tools.base import ToolContext, ToolSpec

YOUTH_MAX_AGE = 34


def run(input: PolicyMatchInput, ctx: ToolContext) -> PolicyMatchOutput:
    eligible = input.age <= YOUTH_MAX_AGE
    rate = 1.5 if input.is_married else 2.0
    return PolicyMatchOutput(
        options=[
            PolicyOption(
                policy_name="청년 전세자금대출 (샘플 데이터)",
                eligible=eligible,
                preferential_rate_percent=rate,
                reference_url="https://www.molit.go.kr",
            )
        ]
    )


TOOL_SPEC = ToolSpec(
    name="policy_matcher",
    description="청년/신혼부부 정책을 비교하고 가/불가·우대금리를 판단합니다",
    input_schema=PolicyMatchInput,
    output_schema=PolicyMatchOutput,
    entrypoint=run,
)
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `.venv/Scripts/pytest tests/features/test_policy_matcher.py -v`
Expected: PASS (4 tests)

- [ ] **Step 7: Commit**

```bash
git add backend/app/features backend/tests/features/__init__.py backend/tests/features/test_policy_matcher.py
git commit -m "feat: add policy_matcher tool (placeholder logic)"
```

---

## Task 6: Feature — savings_planner (placeholder)

**Files:**
- Create: `backend/app/features/savings_planner/__init__.py`
- Create: `backend/app/features/savings_planner/schemas.py`
- Create: `backend/app/features/savings_planner/tool.py`
- Test: `backend/tests/features/test_savings_planner.py`

**Interfaces:**
- Consumes: `app.tools.base.ToolSpec`, `ToolContext` (Task 2)
- Produces: `app.features.savings_planner.tool.TOOL_SPEC` (named `"savings_planner"`) — Task 9 registers this
- Produces: `app.features.savings_planner.tool.run(input: SavingsPlanInput, ctx: ToolContext) -> SavingsPlanOutput`

- [ ] **Step 1: Create empty `__init__.py`**

```bash
mkdir -p backend/app/features/savings_planner
touch backend/app/features/savings_planner/__init__.py
```

- [ ] **Step 2: Write the failing test `backend/tests/features/test_savings_planner.py`**

```python
import math

from app.features.savings_planner.schemas import SavingsPlanInput
from app.features.savings_planner.tool import TOOL_SPEC, run
from app.tools.base import ToolContext


def test_tool_spec_has_expected_name():
    assert TOOL_SPEC.name == "savings_planner"
    assert TOOL_SPEC.entrypoint is run


def test_run_computes_monthly_required_amount():
    ctx = ToolContext(user_id=1, db=None)
    result = run(SavingsPlanInput(monthly_income_krw=3_000_000, goal_amount_krw=12_000_000, goal_months=12), ctx)
    assert result.monthly_required_krw == 1_000_000


def test_run_rounds_up_when_goal_does_not_divide_evenly():
    ctx = ToolContext(user_id=1, db=None)
    result = run(SavingsPlanInput(monthly_income_krw=3_000_000, goal_amount_krw=1_000_000, goal_months=3), ctx)
    assert result.monthly_required_krw == math.ceil(1_000_000 / 3)


def test_run_allocates_full_required_amount_to_savings_category():
    ctx = ToolContext(user_id=1, db=None)
    result = run(SavingsPlanInput(monthly_income_krw=3_000_000, goal_amount_krw=6_000_000, goal_months=6), ctx)
    assert sum(a.monthly_amount_krw for a in result.allocations) == result.monthly_required_krw
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `.venv/Scripts/pytest tests/features/test_savings_planner.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Write `app/features/savings_planner/schemas.py`**

```python
from pydantic import BaseModel


class SavingsPlanInput(BaseModel):
    monthly_income_krw: int
    goal_amount_krw: int
    goal_months: int


class SavingsAllocation(BaseModel):
    category: str
    monthly_amount_krw: int


class SavingsPlanOutput(BaseModel):
    allocations: list[SavingsAllocation]
    monthly_required_krw: int
```

- [ ] **Step 5: Write `app/features/savings_planner/tool.py`**

```python
import math

from app.features.savings_planner.schemas import SavingsAllocation, SavingsPlanInput, SavingsPlanOutput
from app.tools.base import ToolContext, ToolSpec


def run(input: SavingsPlanInput, ctx: ToolContext) -> SavingsPlanOutput:
    monthly_required = math.ceil(input.goal_amount_krw / input.goal_months)
    return SavingsPlanOutput(
        allocations=[SavingsAllocation(category="목표 적금 (샘플 배분)", monthly_amount_krw=monthly_required)],
        monthly_required_krw=monthly_required,
    )


TOOL_SPEC = ToolSpec(
    name="savings_planner",
    description="월급과 목표 금액을 기반으로 저축/적금 배분을 설계합니다",
    input_schema=SavingsPlanInput,
    output_schema=SavingsPlanOutput,
    entrypoint=run,
)
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `.venv/Scripts/pytest tests/features/test_savings_planner.py -v`
Expected: PASS (4 tests)

- [ ] **Step 7: Commit**

```bash
git add backend/app/features/savings_planner backend/tests/features/test_savings_planner.py
git commit -m "feat: add savings_planner tool (placeholder logic)"
```

---

## Task 7: Feature — subscription_report (placeholder)

**Files:**
- Create: `backend/app/features/subscription_report/__init__.py`
- Create: `backend/app/features/subscription_report/schemas.py`
- Create: `backend/app/features/subscription_report/tool.py`
- Test: `backend/tests/features/test_subscription_report.py`

**Interfaces:**
- Consumes: `app.tools.base.ToolSpec`, `ToolContext` (Task 2)
- Produces: `app.features.subscription_report.tool.TOOL_SPEC` (named `"subscription_report"`) — Task 9 registers this
- Produces: `app.features.subscription_report.tool.run(input: SubscriptionReportInput, ctx: ToolContext) -> SubscriptionReportOutput`

- [ ] **Step 1: Create empty `__init__.py`**

```bash
mkdir -p backend/app/features/subscription_report
touch backend/app/features/subscription_report/__init__.py
```

- [ ] **Step 2: Write the failing test `backend/tests/features/test_subscription_report.py`**

```python
from app.features.subscription_report.schemas import SubscriptionReportInput
from app.features.subscription_report.tool import TOOL_SPEC, run
from app.tools.base import ToolContext


def test_tool_spec_has_expected_name():
    assert TOOL_SPEC.name == "subscription_report"
    assert TOOL_SPEC.entrypoint is run


def test_run_returns_items_and_matching_total():
    ctx = ToolContext(user_id=1, db=None)
    result = run(SubscriptionReportInput(month="2026-07"), ctx)
    assert len(result.items) >= 1
    assert result.total_cost_krw == sum(item.monthly_cost_krw for item in result.items)
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `.venv/Scripts/pytest tests/features/test_subscription_report.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Write `app/features/subscription_report/schemas.py`**

```python
from pydantic import BaseModel


class SubscriptionReportInput(BaseModel):
    month: str  # "YYYY-MM"


class SubscriptionItem(BaseModel):
    service_name: str
    monthly_cost_krw: int


class SubscriptionReportOutput(BaseModel):
    month: str
    items: list[SubscriptionItem]
    total_cost_krw: int
```

- [ ] **Step 5: Write `app/features/subscription_report/tool.py`**

```python
from app.features.subscription_report.schemas import (
    SubscriptionItem,
    SubscriptionReportInput,
    SubscriptionReportOutput,
)
from app.tools.base import ToolContext, ToolSpec


def run(input: SubscriptionReportInput, ctx: ToolContext) -> SubscriptionReportOutput:
    items = [
        SubscriptionItem(service_name="Netflix (샘플)", monthly_cost_krw=17_000),
        SubscriptionItem(service_name="YouTube Premium (샘플)", monthly_cost_krw=14_900),
    ]
    return SubscriptionReportOutput(
        month=input.month,
        items=items,
        total_cost_krw=sum(item.monthly_cost_krw for item in items),
    )


TOOL_SPEC = ToolSpec(
    name="subscription_report",
    description="한 달간의 구독 서비스 사용 내역과 총 비용을 리포트합니다",
    input_schema=SubscriptionReportInput,
    output_schema=SubscriptionReportOutput,
    entrypoint=run,
)
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `.venv/Scripts/pytest tests/features/test_subscription_report.py -v`
Expected: PASS (2 tests)

- [ ] **Step 7: Commit**

```bash
git add backend/app/features/subscription_report backend/tests/features/test_subscription_report.py
git commit -m "feat: add subscription_report tool (placeholder logic)"
```

---

## Task 8: Feature — card_spending_report (placeholder)

**Files:**
- Create: `backend/app/features/card_spending_report/__init__.py`
- Create: `backend/app/features/card_spending_report/schemas.py`
- Create: `backend/app/features/card_spending_report/tool.py`
- Test: `backend/tests/features/test_card_spending_report.py`

**Interfaces:**
- Consumes: `app.tools.base.ToolSpec`, `ToolContext` (Task 2)
- Produces: `app.features.card_spending_report.tool.TOOL_SPEC` (named `"card_spending_report"`) — Task 9 registers this
- Produces: `app.features.card_spending_report.tool.run(input: CardSpendingReportInput, ctx: ToolContext) -> CardSpendingReportOutput`

- [ ] **Step 1: Create empty `__init__.py`**

```bash
mkdir -p backend/app/features/card_spending_report
touch backend/app/features/card_spending_report/__init__.py
```

- [ ] **Step 2: Write the failing test `backend/tests/features/test_card_spending_report.py`**

```python
from app.features.card_spending_report.schemas import CardSpendingReportInput
from app.features.card_spending_report.tool import TOOL_SPEC, run
from app.tools.base import ToolContext


def test_tool_spec_has_expected_name():
    assert TOOL_SPEC.name == "card_spending_report"
    assert TOOL_SPEC.entrypoint is run


def test_run_returns_categories_and_matching_total():
    ctx = ToolContext(user_id=1, db=None)
    result = run(CardSpendingReportInput(month="2026-07"), ctx)
    assert len(result.categories) >= 1
    assert result.total_amount_krw == sum(c.amount_krw for c in result.categories)
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `.venv/Scripts/pytest tests/features/test_card_spending_report.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Write `app/features/card_spending_report/schemas.py`**

```python
from pydantic import BaseModel


class CardSpendingReportInput(BaseModel):
    month: str  # "YYYY-MM"


class CategorySpending(BaseModel):
    category: str
    amount_krw: int


class CardSpendingReportOutput(BaseModel):
    month: str
    categories: list[CategorySpending]
    total_amount_krw: int
```

- [ ] **Step 5: Write `app/features/card_spending_report/tool.py`**

```python
from app.features.card_spending_report.schemas import (
    CardSpendingReportInput,
    CardSpendingReportOutput,
    CategorySpending,
)
from app.tools.base import ToolContext, ToolSpec


def run(input: CardSpendingReportInput, ctx: ToolContext) -> CardSpendingReportOutput:
    categories = [
        CategorySpending(category="식비 (샘플)", amount_krw=320_000),
        CategorySpending(category="교통 (샘플)", amount_krw=95_000),
        CategorySpending(category="쇼핑 (샘플)", amount_krw=210_000),
    ]
    return CardSpendingReportOutput(
        month=input.month,
        categories=categories,
        total_amount_krw=sum(c.amount_krw for c in categories),
    )


TOOL_SPEC = ToolSpec(
    name="card_spending_report",
    description="한 달간의 카드 사용 내역을 카테고리별로 분석해 리포트합니다",
    input_schema=CardSpendingReportInput,
    output_schema=CardSpendingReportOutput,
    entrypoint=run,
)
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `.venv/Scripts/pytest tests/features/test_card_spending_report.py -v`
Expected: PASS (2 tests)

- [ ] **Step 7: Commit**

```bash
git add backend/app/features/card_spending_report backend/tests/features/test_card_spending_report.py
git commit -m "feat: add card_spending_report tool (placeholder logic)"
```

---

## Task 9: Feature Registration + Generic Tools Router

**Files:**
- Modify: `backend/app/features/__init__.py`
- Create: `backend/app/tools/router.py`
- Modify: `backend/app/main.py` — call `register_all_tools()`, include `tools_router`
- Test: `backend/tests/test_tools_router.py`

**Interfaces:**
- Consumes: `TOOL_SPEC` from all 4 feature `tool.py` modules (Tasks 5-8), `app.tools.registry.registry`, `get_tool_registry` (Task 2), `app.auth.router.get_current_user` (Task 3)
- Produces: `app.features.register_all_tools() -> None` — the **one and only place** a new feature's `TOOL_SPEC` needs to be added
- Produces: routes `POST /tools/{name}` (auth-protected, generic dispatch to any registered tool)

- [ ] **Step 1: Write the failing test `backend/tests/test_tools_router.py`**

```python
def _signup_and_login(client, email="tools-user@example.com"):
    client.post("/auth/signup", json={"email": email, "password": "secret123"})
    login = client.post("/auth/login", json={"email": email, "password": "secret123"})
    return login.json()["access_token"]


def test_calling_registered_tool_returns_its_output(client):
    token = _signup_and_login(client)
    response = client.post(
        "/tools/policy_matcher",
        json={"age": 29, "is_married": False, "annual_income_krw": 40_000_000, "region": "서울"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["options"][0]["eligible"] is True


def test_calling_unknown_tool_returns_404(client):
    token = _signup_and_login(client, email="tools-user2@example.com")
    response = client.post("/tools/does_not_exist", json={}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404


def test_calling_tool_without_auth_returns_401(client):
    response = client.post("/tools/policy_matcher", json={})
    assert response.status_code == 401


def test_calling_tool_with_invalid_payload_returns_400(client):
    token = _signup_and_login(client, email="tools-user3@example.com")
    response = client.post("/tools/policy_matcher", json={"age": "not-a-number"}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 400
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/Scripts/pytest tests/test_tools_router.py -v`
Expected: FAIL — `404 Not Found` for `/tools/policy_matcher` (route doesn't exist yet)

- [ ] **Step 3: Fill in `app/features/__init__.py`**

```python
from app.features.card_spending_report.tool import TOOL_SPEC as CARD_SPENDING_REPORT_SPEC
from app.features.policy_matcher.tool import TOOL_SPEC as POLICY_MATCHER_SPEC
from app.features.savings_planner.tool import TOOL_SPEC as SAVINGS_PLANNER_SPEC
from app.features.subscription_report.tool import TOOL_SPEC as SUBSCRIPTION_REPORT_SPEC
from app.tools.registry import registry

ALL_TOOL_SPECS = [
    POLICY_MATCHER_SPEC,
    SAVINGS_PLANNER_SPEC,
    SUBSCRIPTION_REPORT_SPEC,
    CARD_SPENDING_REPORT_SPEC,
]


def register_all_tools() -> None:
    for spec in ALL_TOOL_SPECS:
        registry.register(spec)
```

*(When adding a new feature later: create `app/features/<name>/tool.py` with its own `TOOL_SPEC`, then add one import + one entry to `ALL_TOOL_SPECS` here. Nothing else in `app/tools/` or `app/main.py` changes.)*

- [ ] **Step 4: Write `app/tools/router.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.router import get_current_user
from app.core.db import get_db
from app.tools.base import ToolContext
from app.tools.errors import ToolExecutionError
from app.tools.registry import ToolRegistry, get_tool_registry

router = APIRouter()


@router.post("/{name}")
def run_tool(
    name: str,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tool_registry: ToolRegistry = Depends(get_tool_registry),
):
    ctx = ToolContext(user_id=current_user.id, db=db)
    try:
        result = tool_registry.execute(name, payload, ctx)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Tool '{name}' not found")
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ToolExecutionError as e:
        raise HTTPException(status_code=400, detail=e.message)
    return result
```

Note: `ToolRegistry.execute()` calls `spec.input_schema.model_validate(raw_input)` directly (not wrapped in the `try/except Exception` around the entrypoint call), so a `ValidationError` propagates up to this router uncaught by `ToolExecutionError` — hence the separate `except ValidationError` branch above.

- [ ] **Step 5: Wire registration + router into `app/main.py`**

```python
from fastapi import FastAPI

from app.auth.models import User  # noqa: F401
from app.auth.router import router as auth_router
from app.core.db import Base, engine
from app.features import register_all_tools
from app.shared.models import Account, Transaction  # noqa: F401
from app.tools.router import router as tools_router

register_all_tools()
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Finance AI Hackathon")
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(tools_router, prefix="/tools", tags=["tools"])


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `.venv/Scripts/pytest tests/test_tools_router.py -v`
Expected: PASS (4 tests)

- [ ] **Step 7: Run the full test suite to confirm nothing regressed**

Run: `.venv/Scripts/pytest -v`
Expected: PASS (all tests across all previous tasks)

- [ ] **Step 8: Commit**

```bash
git add backend/app/features/__init__.py backend/app/tools/router.py backend/app/main.py backend/tests/test_tools_router.py
git commit -m "feat: register all feature tools and expose generic POST /tools/{name}"
```

---

## Task 10: LLM Provider Abstraction (Claude + OpenAI)

**Files:**
- Create: `backend/app/llm/__init__.py`
- Create: `backend/app/llm/base.py`
- Create: `backend/app/llm/claude_provider.py`
- Create: `backend/app/llm/openai_provider.py`
- Create: `backend/app/llm/factory.py`
- Test: `backend/tests/llm/__init__.py`
- Test: `backend/tests/llm/test_tool_conversion.py`
- Test: `backend/tests/llm/test_factory.py`

**Interfaces:**
- Consumes: `app.tools.base.ToolSpec` (Task 2)
- Produces: `app.llm.base.Message(role: Literal["user","assistant","system"], content: str)`, `ToolCallRequest(name: str, arguments: dict)`, `LLMResponse(content: str | None, tool_calls: list[ToolCallRequest])`, `LLMProvider` (Protocol with `chat(messages: list[Message], tools: list[ToolSpec]) -> LLMResponse`)
- Produces: `app.llm.factory.get_provider() -> LLMProvider` — Task 11 (chat router) depends on this

- [ ] **Step 1: Create empty `__init__.py` files**

```bash
mkdir -p backend/app/llm backend/tests/llm
touch backend/app/llm/__init__.py backend/tests/llm/__init__.py
```

- [ ] **Step 2: Write `app/llm/base.py` (no test needed — pure data types, exercised by later tests)**

```python
from typing import Literal, Protocol

from pydantic import BaseModel

from app.tools.base import ToolSpec


class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ToolCallRequest(BaseModel):
    name: str
    arguments: dict


class LLMResponse(BaseModel):
    content: str | None = None
    tool_calls: list[ToolCallRequest] = []


class LLMProvider(Protocol):
    def chat(self, messages: list[Message], tools: list[ToolSpec]) -> LLMResponse: ...
```

- [ ] **Step 3: Write the failing test `backend/tests/llm/test_tool_conversion.py`**

```python
from pydantic import BaseModel

from app.llm.claude_provider import _to_claude_tools
from app.llm.openai_provider import _to_openai_tools
from app.tools.base import ToolSpec


class SampleInput(BaseModel):
    x: int


class SampleOutput(BaseModel):
    y: int


def _sample_spec() -> ToolSpec:
    return ToolSpec(
        name="sample_tool",
        description="a sample tool",
        input_schema=SampleInput,
        output_schema=SampleOutput,
        entrypoint=lambda i, ctx: SampleOutput(y=i.x),
    )


def test_to_claude_tools_produces_name_description_input_schema():
    result = _to_claude_tools([_sample_spec()])
    assert result == [
        {
            "name": "sample_tool",
            "description": "a sample tool",
            "input_schema": SampleInput.model_json_schema(),
        }
    ]


def test_to_openai_tools_produces_function_wrapper():
    result = _to_openai_tools([_sample_spec()])
    assert result == [
        {
            "type": "function",
            "function": {
                "name": "sample_tool",
                "description": "a sample tool",
                "parameters": SampleInput.model_json_schema(),
            },
        }
    ]
```

- [ ] **Step 4: Run the tests to verify they fail**

Run: `.venv/Scripts/pytest tests/llm/test_tool_conversion.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.llm.claude_provider'`

- [ ] **Step 5: Write `app/llm/claude_provider.py`**

```python
import anthropic

from app.core.config import settings
from app.llm.base import LLMResponse, Message, ToolCallRequest
from app.tools.base import ToolSpec


def _to_claude_tools(tools: list[ToolSpec]) -> list[dict]:
    return [
        {
            "name": t.name,
            "description": t.description,
            "input_schema": t.input_schema.model_json_schema(),
        }
        for t in tools
    ]


class ClaudeProvider:
    def __init__(self) -> None:
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def chat(self, messages: list[Message], tools: list[ToolSpec]) -> LLMResponse:
        system_messages = [m.content for m in messages if m.role == "system"]
        conversation = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]

        create_kwargs: dict = {
            "model": settings.claude_model,
            "max_tokens": 1024,
            "messages": conversation,
            "tools": _to_claude_tools(tools),
        }
        if system_messages:
            # The Anthropic SDK's `system` param must be omitted entirely when
            # absent — passing `system=None` sends a literal null the API rejects.
            create_kwargs["system"] = system_messages[0]

        response = self._client.messages.create(**create_kwargs)

        content_text: str | None = None
        tool_calls: list[ToolCallRequest] = []
        for block in response.content:
            if block.type == "text":
                content_text = block.text
            elif block.type == "tool_use":
                tool_calls.append(ToolCallRequest(name=block.name, arguments=block.input))

        return LLMResponse(content=content_text, tool_calls=tool_calls)
```

- [ ] **Step 6: Write `app/llm/openai_provider.py`**

```python
import json

import openai

from app.core.config import settings
from app.llm.base import LLMResponse, Message, ToolCallRequest
from app.tools.base import ToolSpec


def _to_openai_tools(tools: list[ToolSpec]) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.input_schema.model_json_schema(),
            },
        }
        for t in tools
    ]


class OpenAIProvider:
    def __init__(self) -> None:
        self._client = openai.OpenAI(api_key=settings.openai_api_key)

    def chat(self, messages: list[Message], tools: list[ToolSpec]) -> LLMResponse:
        response = self._client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            tools=_to_openai_tools(tools),
        )

        choice = response.choices[0].message
        tool_calls = [
            ToolCallRequest(name=tc.function.name, arguments=json.loads(tc.function.arguments))
            for tc in (choice.tool_calls or [])
        ]

        return LLMResponse(content=choice.content, tool_calls=tool_calls)
```

- [ ] **Step 7: Run the tool-conversion tests to verify they pass**

Run: `.venv/Scripts/pytest tests/llm/test_tool_conversion.py -v`
Expected: PASS (2 tests)

- [ ] **Step 8: Write the failing test `backend/tests/llm/test_factory.py`**

```python
import pytest

from app.llm.claude_provider import ClaudeProvider
from app.llm.factory import get_provider
from app.llm.openai_provider import OpenAIProvider


def test_get_provider_returns_claude_by_default(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.llm_provider", "claude")
    monkeypatch.setattr("app.core.config.settings.anthropic_api_key", "test-key")
    provider = get_provider()
    assert isinstance(provider, ClaudeProvider)


def test_get_provider_returns_openai_when_configured(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.llm_provider", "openai")
    monkeypatch.setattr("app.core.config.settings.openai_api_key", "test-key")
    provider = get_provider()
    assert isinstance(provider, OpenAIProvider)


def test_get_provider_raises_on_unknown_provider(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.llm_provider", "not-a-real-provider")
    with pytest.raises(ValueError):
        get_provider()
```

- [ ] **Step 9: Run the test to verify it fails**

Run: `.venv/Scripts/pytest tests/llm/test_factory.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.llm.factory'`

- [ ] **Step 10: Write `app/llm/factory.py`**

```python
from app.core.config import settings
from app.llm.base import LLMProvider
from app.llm.claude_provider import ClaudeProvider
from app.llm.openai_provider import OpenAIProvider


def get_provider() -> LLMProvider:
    if settings.llm_provider == "claude":
        return ClaudeProvider()
    if settings.llm_provider == "openai":
        return OpenAIProvider()
    raise ValueError(f"Unknown LLM_PROVIDER: {settings.llm_provider}")
```

- [ ] **Step 11: Run the test to verify it passes**

Run: `.venv/Scripts/pytest tests/llm/test_factory.py -v`
Expected: PASS (3 tests)

- [ ] **Step 12: Commit**

```bash
git add backend/app/llm backend/tests/llm
git commit -m "feat: add LLM provider abstraction (Claude, OpenAI) with tool-schema conversion"
```

---

## Task 11: Chat Orchestration Router

**Files:**
- Create: `backend/app/llm/chat_router.py`
- Modify: `backend/app/main.py` — include `chat_router`
- Test: `backend/tests/test_chat_router.py`

**Interfaces:**
- Consumes: `app.llm.base.{Message, LLMResponse, ToolCallRequest, LLMProvider}` (Task 10), `app.llm.factory.get_provider` (Task 10), `app.tools.registry.{registry, get_tool_registry, ToolRegistry}` (Task 2/9), `app.tools.base.ToolContext` (Task 2), `app.tools.errors.ToolExecutionError` (Task 2), `app.auth.router.get_current_user` (Task 3)
- Produces: route `POST /chat` (auth-protected)
- Produces: `app.llm.chat_router.get_llm_provider() -> LLMProvider` (FastAPI dependency, overridable in tests)

- [ ] **Step 1: Write the failing tests in `backend/tests/test_chat_router.py`**

```python
from pydantic import BaseModel

from app.llm.base import LLMResponse, ToolCallRequest
from app.llm.chat_router import get_llm_provider
from app.main import app
from app.tools.base import ToolContext, ToolSpec
from app.tools.registry import ToolRegistry, get_tool_registry


class EchoInput(BaseModel):
    text: str


class EchoOutput(BaseModel):
    echoed: str


def _echo_run(input: EchoInput, ctx: ToolContext) -> EchoOutput:
    return EchoOutput(echoed=input.text)


def _test_registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(
        ToolSpec(
            name="echo_tool",
            description="echoes text back",
            input_schema=EchoInput,
            output_schema=EchoOutput,
            entrypoint=_echo_run,
        )
    )
    return reg


class FakeProvider:
    def __init__(self, responses: list[LLMResponse]):
        self._responses = iter(responses)

    def chat(self, messages, tools):
        return next(self._responses)


def _login(client) -> str:
    client.post("/auth/signup", json={"email": "chat-user@example.com", "password": "secret123"})
    login = client.post("/auth/login", json={"email": "chat-user@example.com", "password": "secret123"})
    return login.json()["access_token"]


def test_chat_returns_direct_content_when_no_tool_call(client):
    token = _login(client)
    app.dependency_overrides[get_llm_provider] = lambda: FakeProvider(
        [LLMResponse(content="안녕하세요!", tool_calls=[])]
    )
    app.dependency_overrides[get_tool_registry] = _test_registry

    response = client.post("/chat", json={"message": "hi"}, headers={"Authorization": f"Bearer {token}"})

    app.dependency_overrides.pop(get_llm_provider, None)
    app.dependency_overrides.pop(get_tool_registry, None)

    assert response.status_code == 200
    assert response.json()["reply"] == "안녕하세요!"


def test_chat_executes_tool_call_then_returns_final_content(client):
    token = _login(client)
    app.dependency_overrides[get_llm_provider] = lambda: FakeProvider(
        [
            LLMResponse(content=None, tool_calls=[ToolCallRequest(name="echo_tool", arguments={"text": "hello"})]),
            LLMResponse(content="done", tool_calls=[]),
        ]
    )
    app.dependency_overrides[get_tool_registry] = _test_registry

    response = client.post("/chat", json={"message": "please echo hello"}, headers={"Authorization": f"Bearer {token}"})

    app.dependency_overrides.pop(get_llm_provider, None)
    app.dependency_overrides.pop(get_tool_registry, None)

    assert response.status_code == 200
    assert response.json()["reply"] == "done"


def test_chat_requires_auth(client):
    response = client.post("/chat", json={"message": "hi"})
    assert response.status_code == 401


def test_chat_recovers_when_tool_call_has_invalid_arguments(client):
    token = _login(client)
    app.dependency_overrides[get_llm_provider] = lambda: FakeProvider(
        [
            # "text" is required by EchoInput but omitted here — must not 500.
            LLMResponse(content=None, tool_calls=[ToolCallRequest(name="echo_tool", arguments={})]),
            LLMResponse(content="recovered", tool_calls=[]),
        ]
    )
    app.dependency_overrides[get_tool_registry] = _test_registry

    response = client.post("/chat", json={"message": "please echo hello"}, headers={"Authorization": f"Bearer {token}"})

    app.dependency_overrides.pop(get_llm_provider, None)
    app.dependency_overrides.pop(get_tool_registry, None)

    assert response.status_code == 200
    assert response.json()["reply"] == "recovered"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/Scripts/pytest tests/test_chat_router.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.llm.chat_router'`

- [ ] **Step 3: Write `app/llm/chat_router.py`**

```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.router import get_current_user
from app.core.db import get_db
from app.llm.base import LLMProvider, Message
from app.llm.factory import get_provider
from app.tools.base import ToolContext
from app.tools.errors import ToolExecutionError
from app.tools.registry import ToolRegistry, get_tool_registry

router = APIRouter()

MAX_TOOL_ITERATIONS = 5


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


def get_llm_provider() -> LLMProvider:
    return get_provider()


@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    provider: LLMProvider = Depends(get_llm_provider),
    tool_registry: ToolRegistry = Depends(get_tool_registry),
):
    ctx = ToolContext(user_id=current_user.id, db=db)
    tools = tool_registry.all()
    messages = [Message(role="user", content=request.message)]

    response = provider.chat(messages, tools)

    iterations = 0
    while response.tool_calls and iterations < MAX_TOOL_ITERATIONS:
        for call in response.tool_calls:
            try:
                result = tool_registry.execute(call.name, call.arguments, ctx)
                result_text = result.model_dump_json()
            except (KeyError, ValidationError, ToolExecutionError) as e:
                # A bad tool name/arguments from the LLM shouldn't 500 the
                # request — report it back into the conversation so the LLM
                # (or the user) can see what went wrong and retry.
                result_text = f"Error: {e}"
            messages.append(Message(role="assistant", content=f"[calling tool {call.name}]"))
            messages.append(Message(role="user", content=f"[tool result for {call.name}] {result_text}"))
        response = provider.chat(messages, tools)
        iterations += 1

    return ChatResponse(reply=response.content or "")
```

- [ ] **Step 4: Wire the chat router into `app/main.py`**

```python
from fastapi import FastAPI

from app.auth.models import User  # noqa: F401
from app.auth.router import router as auth_router
from app.core.db import Base, engine
from app.features import register_all_tools
from app.llm.chat_router import router as chat_router
from app.shared.models import Account, Transaction  # noqa: F401
from app.tools.router import router as tools_router

register_all_tools()
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Finance AI Hackathon")
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(tools_router, prefix="/tools", tags=["tools"])
app.include_router(chat_router, tags=["chat"])


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `.venv/Scripts/pytest tests/test_chat_router.py -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Run the full backend test suite**

Run: `.venv/Scripts/pytest -v`
Expected: PASS (every test from Tasks 1-11)

- [ ] **Step 7: Commit**

```bash
git add backend/app/llm/chat_router.py backend/app/main.py backend/tests/test_chat_router.py
git commit -m "feat: add POST /chat orchestration loop over LLM provider and tool registry"
```

---

## Task 12: Frontend Scaffold (Next.js — login + chat page)

**Files:**
- Create: `frontend/` (via `create-next-app`)
- Create: `frontend/lib/api.ts`
- Create: `frontend/app/login/page.tsx`
- Create: `frontend/app/chat/page.tsx`
- Modify: `frontend/app/page.tsx`

**Interfaces:**
- Consumes: backend routes `POST /auth/login` (Task 3), `POST /chat` (Task 11)
- Produces: browser pages at `/login` and `/chat`, a token stored in `localStorage` under key `"token"`

This task has no automated tests — it is UI scaffolding. Verify manually by running the dev server and clicking through the flow (Step 7).

- [ ] **Step 1: Scaffold the Next.js app**

```bash
npx create-next-app@latest frontend --typescript --eslint --app --src-dir=false --import-alias "@/*" --tailwind=false --use-npm
```

Answer "No" to any prompt about Turbopack if asked (defaults are fine otherwise).

- [ ] **Step 2: Write `frontend/lib/api.ts`**

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export async function login(email: string, password: string): Promise<string> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    throw new Error("Login failed");
  }
  const data = await res.json();
  return data.access_token as string;
}

export async function sendChatMessage(token: string, message: string): Promise<string> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ message }),
  });
  if (!res.ok) {
    throw new Error("Chat request failed");
  }
  const data = await res.json();
  return data.reply as string;
}
```

- [ ] **Step 3: Write `frontend/app/login/page.tsx`**

```tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/lib/api";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const token = await login(email, password);
      localStorage.setItem("token", token);
      router.push("/chat");
    } catch {
      setError("로그인에 실패했습니다.");
    }
  }

  return (
    <main style={{ maxWidth: 360, margin: "80px auto" }}>
      <h1>로그인</h1>
      <form onSubmit={handleSubmit}>
        <input
          type="email"
          placeholder="이메일"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          style={{ display: "block", width: "100%", marginBottom: 8 }}
        />
        <input
          type="password"
          placeholder="비밀번호"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          style={{ display: "block", width: "100%", marginBottom: 8 }}
        />
        {error && <p style={{ color: "red" }}>{error}</p>}
        <button type="submit">로그인</button>
      </form>
    </main>
  );
}
```

- [ ] **Step 4: Write `frontend/app/chat/page.tsx`**

```tsx
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { sendChatMessage } from "@/lib/api";

type ChatEntry = { role: "user" | "assistant"; content: string };

export default function ChatPage() {
  const [token, setToken] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [history, setHistory] = useState<ChatEntry[]>([]);
  const router = useRouter();

  useEffect(() => {
    const stored = localStorage.getItem("token");
    if (!stored) {
      router.push("/login");
      return;
    }
    setToken(stored);
  }, [router]);

  async function handleSend() {
    if (!token || !input.trim()) return;
    const userMessage = input;
    setHistory((h) => [...h, { role: "user", content: userMessage }]);
    setInput("");
    try {
      const reply = await sendChatMessage(token, userMessage);
      setHistory((h) => [...h, { role: "assistant", content: reply }]);
    } catch {
      setHistory((h) => [...h, { role: "assistant", content: "(오류가 발생했습니다)" }]);
    }
  }

  return (
    <main style={{ maxWidth: 600, margin: "40px auto" }}>
      <h1>AI 금융 비서</h1>
      <div style={{ minHeight: 300, border: "1px solid #ccc", padding: 12, marginBottom: 12 }}>
        {history.map((entry, i) => (
          <p key={i}>
            <strong>{entry.role === "user" ? "나" : "AI"}:</strong> {entry.content}
          </p>
        ))}
      </div>
      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && handleSend()}
        style={{ width: "80%" }}
      />
      <button onClick={handleSend}>전송</button>
    </main>
  );
}
```

- [ ] **Step 5: Modify `frontend/app/page.tsx` to redirect to `/login`**

```tsx
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    router.push("/login");
  }, [router]);

  return null;
}
```

- [ ] **Step 6: Add `frontend/.env.local`**

```
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

- [ ] **Step 7: Manually verify the flow**

Start the backend: `backend/.venv/Scripts/uvicorn app.main:app --reload --app-dir backend` (run from repo root, or `cd backend` first and drop `--app-dir`).
Start the frontend: `cd frontend && npm run dev`.
Open `http://localhost:3000` in a browser — confirm it redirects to `/login`. Sign up a user via `POST http://localhost:8000/auth/signup` (curl or the FastAPI `/docs` UI, since there's no signup page yet), then log in through the `/login` form. Confirm it redirects to `/chat` and that sending a message round-trips (it will hit whichever `LLM_PROVIDER` is configured — if no API key is set, this call will fail; that's expected and acceptable at scaffold stage, confirm instead that the request reaches the backend and returns a clear error rather than the frontend crashing).

- [ ] **Step 8: Commit**

```bash
git add frontend
git commit -m "feat: scaffold Next.js frontend with login and chat pages"
```

---

## Task 13: Final Integration Check

**Files:** none created — verification only.

- [ ] **Step 1: Run the full backend test suite from a clean install**

```bash
cd backend
.venv/Scripts/pytest -v
```

Expected: every test from Tasks 1-11 passes.

- [ ] **Step 2: Start the backend and confirm the OpenAPI docs list every route**

```bash
backend/.venv/Scripts/uvicorn app.main:app --app-dir backend
```

Open `http://localhost:8000/docs` — confirm `/health`, `/auth/signup`, `/auth/login`, `/auth/me`, `/tools/{name}`, `/chat` are all listed.

- [ ] **Step 3: Confirm adding a hypothetical 5th tool would require no core changes**

Read through `app/features/__init__.py` and `app/tools/router.py` — confirm that registering a new tool only requires editing `app/features/__init__.py` (one import + one list entry). No code change needed here; this is a design-conformance check against the spec's Global Constraint. If it doesn't hold, fix `app/features/__init__.py` or `app/tools/router.py` before closing this task.

- [ ] **Step 4: Note follow-up work for a future plan**

No commit for this task — it's verification-only. Confirm with the user that real public-data API integration, real decision algorithms for each feature, and apibazzar.com registration remain explicitly out of scope for this plan (as stated in the spec) and should be planned separately per feature.
