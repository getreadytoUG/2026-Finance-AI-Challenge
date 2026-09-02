from contextlib import asynccontextmanager
from urllib.parse import urlsplit

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware 

from app.auth.models import User  # noqa: F401
from app.auth.router import router as auth_router
from app.auth.service import seed_admin_user
from app.core.config import settings
from app.core.db import Base, SessionLocal, engine
from app.core.schema import ensure_schema
from app.features import register_all_tools
from app.features.admin.router import router as admin_router
from app.features.policy_chat.router import router as policy_chat_router
from app.features.policy_matcher.cache import seed_policy_cache_if_empty
from app.features.policy_matcher.models import PolicyRecommendation  # noqa: F401
from app.features.policy_matcher.recommender import register_daily_recommendation_job, scheduler
from app.features.policy_matcher.router import router as policy_matcher_router
from app.features.savings_planner.models import SavingsLinkedBenefit  # noqa: F401
from app.features.savings_planner.router import router as savings_planner_router
from app.features.savings_simulator.router import router as savings_simulator_router
from app.shared.models import Account, Transaction  # noqa: F401
from app.tools.router import router as tools_router

register_all_tools()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_schema(engine)  # 기존 테이블에 누락된 컬럼 보충 (Alembic 대체)
    db = SessionLocal()
    try:
        seed_policy_cache_if_empty(db)
        seed_admin_user(db)
    finally:
        db.close()
    register_daily_recommendation_job()
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="Finance AI Hackathon", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(tools_router, prefix="/tools", tags=["tools"])
app.include_router(policy_matcher_router, prefix="/policy_matcher", tags=["policy_matcher"])
app.include_router(policy_chat_router, prefix="/policy_chat", tags=["policy_chat"])
app.include_router(admin_router, prefix="/admin", tags=["admin"])
app.include_router(savings_planner_router, prefix="/savings_planner", tags=["savings_planner"])
app.include_router(savings_simulator_router, prefix="/savings_simulator", tags=["savings_simulator"])


@app.get("/health")
def health():
    db_url = urlsplit(settings.database_url)
    return {"status": "ok", "db_scheme": db_url.scheme, "db_host": db_url.hostname}
