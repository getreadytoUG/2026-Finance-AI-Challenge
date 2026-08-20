from pathlib import Path

from pydantic_settings import BaseSettings

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent  # backend/


class Settings(BaseSettings):
    jwt_secret: str = "dev-secret-change-me"
    database_url: str = f"sqlite:///{BACKEND_ROOT / 'app.db'}"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    llm_provider: str = "claude"
    claude_model: str = "claude-sonnet-5"
    openai_model: str = "gpt-4o"
    cors_origins: list[str] = ["http://localhost:3000"]

    model_config = {"env_file": ".env"}


settings = Settings()
