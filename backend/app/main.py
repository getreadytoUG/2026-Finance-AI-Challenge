from fastapi import FastAPI

from app.auth.models import User  # noqa: F401 — ensures table is registered on Base metadata
from app.auth.router import router as auth_router
from app.core.db import Base, engine
from app.shared.models import Account, Transaction  # noqa: F401 — registers tables on Base metadata

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Finance AI Hackathon")
app.include_router(auth_router, prefix="/auth", tags=["auth"])


@app.get("/health")
def health():
    return {"status": "ok"}
