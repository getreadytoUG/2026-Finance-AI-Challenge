from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.models import User  # noqa: F401
from app.auth.router import router as auth_router
from app.core.config import settings
from app.core.db import Base, SessionLocal, engine
from app.features import register_all_tools
from app.features.policy_matcher.cache import seed_policy_cache_if_empty
from app.features.policy_matcher.models import PolicyRecommendation  # noqa: F401
from app.features.policy_matcher.recommender import register_daily_recommendation_job, scheduler
from app.features.policy_matcher.router import router as policy_matcher_router
from app.shared.models import Account, Transaction  # noqa: F401
from app.tools.router import router as tools_router

register_all_tools()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_policy_cache_if_empty(db)
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


@app.get("/health")
def health():
    return {"status": "ok"}
