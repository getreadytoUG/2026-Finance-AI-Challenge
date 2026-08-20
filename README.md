# 2026-Finance-AI-Challenge
2026's Finance AI Callenge

## Setup

### Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
cp .env.example .env   # then fill in JWT_SECRET and an LLM API key
.venv/Scripts/uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend expects the backend at `http://localhost:8000` and runs on `http://localhost:3000`.
