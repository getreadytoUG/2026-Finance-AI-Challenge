# 정책 자동 추천 (매일 배치 + 앱 내 알림) 설계

## 배경 및 목표

`policy_matcher`는 현재 사용자가 폼에 나이/혼인여부/소득/지역을 매번 입력해야 결과를 볼 수 있는 대화형(pull) 기능이다([backend/app/features/policy_matcher/tool.py](../../../backend/app/features/policy_matcher/tool.py)). 이 스펙은 여기에 push형 기능을 추가한다: 유저가 프로필을 한 번 저장해두면, 매일 온통청년 API를 조회해서 새로 맞는 정책이 나왔을 때 앱 내 알림 목록에 쌓아준다.

## 범위

**포함**: 유저 프로필 저장(나이/혼인여부/소득/지역), 매칭 로직 공유화, 정책 식별자 추가, 추천 저장 테이블, 전체 유저 대상 일일 배치 + 스케줄러, 로그인 유저 본인만 즉시 갱신하는 수동 트리거, 추천 목록 조회 API, 프론트엔드 "추천" 탭.

**포함하지 않음**: 이메일/푸시 알림, 다른 3개 기능(savings_planner 등)의 추천화, 읽음/안읽음 상태 추적(추천 목록은 항상 전체를 최신순으로 보여준다 — v1에서는 단순함을 우선한다).

## 아키텍처

### 1. 유저 프로필 확장

`backend/app/auth/models.py`의 `User`에 nullable 컬럼 4개 추가:

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

`backend/app/auth/schemas.py`에 추가:

```python
class ProfileUpdateRequest(BaseModel):
    age: int
    is_married: bool
    annual_income_krw: int
    region: str
```

(부분 업데이트가 아니라 4개 필드를 한 번에 채우는 단일 폼 제출 방식 — `policy_matcher`의 `PolicyMatchInput`과 필드가 동일하다.)

`UserOut`에 nullable 필드 4개 추가해서 `/auth/me`가 프로필 완성 여부를 그대로 보여주게 한다:

```python
class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    age: int | None = None
    is_married: bool | None = None
    annual_income_krw: int | None = None
    region: str | None = None
```

`backend/app/auth/router.py`에 추가:

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

### 2. 매칭 로직 공유화

지금 `tool.py`에 있는 `_is_eligible`([backend/app/features/policy_matcher/tool.py:6-23](../../../backend/app/features/policy_matcher/tool.py))을 새 파일 `backend/app/features/policy_matcher/matching.py`로 옮기고 이름을 공개 함수로 바꾼다:

```python
from app.features.policy_matcher.schemas import PolicyMatchInput
from app.features.policy_matcher.youth_center_client import RawYouthPolicy


def is_eligible(policy: RawYouthPolicy, input: PolicyMatchInput) -> bool:
    if policy.min_age is not None and input.age < policy.min_age:
        return False
    if policy.max_age is not None and input.age > policy.max_age:
        return False
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

`tool.py`의 `run()`은 이 함수를 import해서 쓰도록 바뀌고(로직 자체는 그대로, 위치만 이동), 새로 만들 `recommender.py`도 같은 함수를 재사용한다. 이렇게 하면 "매칭 조건이 뭐냐"의 정답이 한 곳에만 있다.

### 3. 정책 식별자 추가 (중복 추천 방지용)

`youth_center_client.py`의 `RawYouthPolicy`에 `policy_id: str` 필드를 추가하고, `_parse_youth_policy_xml()`에서 추정 태그(`plcyNo`)로 채운다 — 기존에 이미 있는 "필드명 불확실성은 이 함수 안에만 격리한다" 패턴을 그대로 따른다:

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

`_parse_youth_policy_xml()`의 `RawYouthPolicy(...)` 생성부에 `policy_id=_text(item, "plcyNo"),` 한 줄 추가. `plcyNo`도 다른 필드들과 마찬가지로 미검증 추정치이므로, 추천 저장 시점에는 `policy_id`가 빈 문자열일 경우 `policy_name`을 대체 키로 쓴다(아래 4번 참고) — 실제 응답에 `plcyNo`가 없거나 이름이 다르더라도 중복 방지 기능 자체는 깨지지 않는다.

### 4. 추천 저장 테이블

새 파일 `backend/app/features/policy_matcher/models.py`:

```python
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint

from app.core.db import Base


class PolicyRecommendation(Base):
    __tablename__ = "policy_recommendations"
    __table_args__ = (UniqueConstraint("user_id", "policy_key", name="uq_policy_recommendation_user_policy"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    policy_key = Column(String, nullable=False)  # policy_id, or policy_name if policy_id was blank
    policy_name = Column(String, nullable=False)
    benefit_description = Column(String, nullable=False)
    application_period = Column(String, nullable=False)
    reference_url = Column(String, nullable=False)
    matched_at = Column(DateTime, nullable=False)
```

`backend/app/main.py`에 `from app.features.policy_matcher.models import PolicyRecommendation  # noqa: F401`을 추가해 테이블이 `Base.metadata`에 등록되게 한다(기존 `shared/models.py` 임포트와 동일한 패턴).

### 5. 배치 엔진

새 파일 `backend/app/features/policy_matcher/recommender.py`:

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
    return total_created
```

**의도적으로 기존 원칙과 다른 지점**: 지금까지 `policy_matcher`의 원칙은 "API 호출 실패는 그대로 예외를 던진다"였다(대화형 `/tools/policy_matcher`, 수동 갱신 엔드포인트는 이 원칙을 그대로 따른다 — 아래 7번 참고). 하지만 `run_recommendation_batch_for_all_users`는 다르다: 한 유저 처리 중 예외(주로 `fetch_policies` 실패)가 나도 나머지 유저 처리를 막으면 안 되므로, 유저 단위로 캐치해서 로그만 남기고 다음 유저로 넘어간다. 이건 "여러 유저를 순회하는 배치"라는 새로운 문맥에서만 적용되는 예외이고, 단일 유저 대상 경로에는 적용되지 않는다.

### 6. 스케줄러

`requirements.txt`에 `apscheduler` 추가.

`backend/app/main.py`의 기존 `lifespan`에 스케줄러를 붙인다:

```python
from apscheduler.schedulers.background import BackgroundScheduler

from app.core.db import SessionLocal
from app.features.policy_matcher.recommender import run_recommendation_batch_for_all_users

scheduler = BackgroundScheduler()


def _run_daily_recommendation_job() -> None:
    db = SessionLocal()
    try:
        run_recommendation_batch_for_all_users(db)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    scheduler.add_job(_run_daily_recommendation_job, "cron", hour=3, id="daily_policy_recommendation")
    scheduler.start()
    yield
    scheduler.shutdown()
```

`SessionLocal`은 `app/core/db.py`에 이미 있다(`get_db()`가 내부적으로 쓰는 것과 동일한 세션 팩토리) — 스케줄된 잡은 FastAPI 요청 컨텍스트 밖에서 돌기 때문에 `Depends(get_db)`를 못 쓰고 직접 세션을 열고 닫는다.

### 7. API 엔드포인트

새 파일 `backend/app/features/policy_matcher/router.py`:

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

이 라우터는 프로필이 미완성인 유저가 `/recommendations/refresh`를 호출하면 `run_recommendation_batch_for_user`가 조용히 0을 반환한다(에러 아님 — 프론트가 "먼저 프로필을 채워주세요"를 보여줄지는 `/auth/me`의 프로필 완성 여부로 판단한다).

`backend/app/features/policy_matcher/schemas.py`에 추가:

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

`backend/app/main.py`에 라우터 등록:

```python
app.include_router(policy_matcher_router, prefix="/policy_matcher", tags=["policy_matcher"])
```

### 8. 프론트엔드

새 탭 `frontend/app/(app)/recommendations/page.tsx` (경로/이름은 구현 시 다른 탭과의 일관성에 맞춰 확정):

- 로드 시 `GET /auth/me`로 프로필 완성 여부 확인
- 미완성이면: 나이/혼인여부/소득/지역 입력 폼 → `PUT /auth/profile` 제출
- 완성이면: `GET /policy_matcher/recommendations`로 목록 표시(최신순, 정책명/지원내용/신청기간/링크) + "지금 갱신" 버튼(`POST /policy_matcher/recommendations/refresh` 호출 후 목록 재조회)
- `frontend/app/(app)/layout.tsx`의 탭 네비게이션에 새 탭 추가

## 데이터 흐름

**일일 배치**: 스케줄러(매일 03:00) → `run_recommendation_batch_for_all_users` → 프로필 완성된 유저 순회 → 유저별 `fetch_policies(query=user.region)` → `is_eligible`로 매칭 → 새 `policy_key`만 `PolicyRecommendation`에 저장.

**수동 갱신**: 유저가 "지금 갱신" 클릭 → `POST /policy_matcher/recommendations/refresh` → `run_recommendation_batch_for_user`(본인만, 동기 실행) → 갱신된 개수 반환 → 프론트가 목록 재조회.

**목록 조회**: `GET /policy_matcher/recommendations` → 유저 본인의 `PolicyRecommendation` 최신순 반환.

## 에러 처리

- `run_recommendation_batch_for_user`(단일 유저 경로: 수동 갱신, 배치 내부에서 개별 호출될 때): `fetch_policies` 실패 시 예외를 그대로 던진다 — 수동 갱신 엔드포인트는 이게 그대로 500으로 노출된다(기존 `policy_matcher` 원칙과 동일).
- `run_recommendation_batch_for_all_users`(전체 유저 배치): 유저 단위로 예외를 캐치·로그하고 계속 진행한다(위 5번에서 설명한 의도적 예외).
- 프로필 미완성 유저는 조용히 스킵(에러 아님).
- 동시성 엣지 케이스: 유저가 "지금 갱신"을 누른 순간 마침 일일 배치가 같은 유저를 처리 중이면 `(user_id, policy_key)` 유니크 제약에 걸려 `IntegrityError`가 날 수 있다. 해커톤 규모의 동시 접속에서는 발생 가능성이 낮고, 발생해도 재시도하면 그때는 이미 다른 쪽이 저장한 뒤라 정상 동작하므로 이번 스펙에서는 별도 처리(재시도/락)를 넣지 않는다.

## 테스트

- `matching.py`: 기존 `tool.py`의 `_is_eligible` 테스트를 그대로 옮겨온다(이름만 `is_eligible`로).
- `recommender.py`: 프로필 미완성 스킵, 적격 정책 저장, 이미 저장된 `policy_key`는 중복 저장 안 함(같은 함수를 두 번 호출해도 두 번째는 0건), `run_recommendation_batch_for_all_users`에서 한 유저의 `fetch_policies` 예외가 다른 유저 처리를 막지 않음 — 이상 4가지를 `fetch_policies`를 monkeypatch해서 검증.
- `policy_matcher/router.py`: 인증 필요, 갱신 후 목록에 반영되는지, 프로필 미완성 유저가 갱신해도 에러 없이 0건 반환하는지.
- `auth/router.py`의 `PUT /auth/profile`: 프로필 업데이트 후 `/auth/me`에 반영되는지.
- 스케줄러 자체: "매일 3시에 실제로 도는지"는 테스트하지 않는다. `main.py`가 시작될 때 `scheduler.get_jobs()`에 `daily_policy_recommendation` 잡이 등록되어 있는지만 가볍게 확인한다(잡이 등록됐다 = 배선이 맞다는 뜻이지, 크론이 정확한 시각에 실행된다는 걸 증명하진 않는다).

## 사용자가 해야 할 일

이 기능은 기존 `YOUTH_CENTER_API_KEY`를 그대로 재사용하므로 추가로 발급받을 것은 없다. 배포 시 스케줄러가 서버 프로세스 안에서 도므로 Cloudtype 쪽에 별도 cron 설정은 필요 없다(단, 서버가 재시작되면 스케줄이 재설정되고 마지막 실행 시각은 기억하지 못한다는 한계는 README에 남겨둔다).
