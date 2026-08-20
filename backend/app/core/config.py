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
