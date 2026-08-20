from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.models import User  # noqa: F401
from app.auth.router import router as auth_router
from app.core.config import settings
from app.core.db import Base, engine
from app.features import register_all_tools
from app.shared.models import Account, Transaction  # noqa: F401
from app.tools.router import router as tools_router

register_all_tools()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Finance AI Hackathon", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(tools_router, prefix="/tools", tags=["tools"])


@app.get("/health")
def health():
    return {"status": "ok"}
