from fastapi import FastAPI

app = FastAPI(title="Finance AI Hackathon")


@app.get("/health")
def health():
    return {"status": "ok"}
