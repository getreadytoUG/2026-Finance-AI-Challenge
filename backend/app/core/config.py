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
    cors_origins: str = "http://localhost:3000"
    youth_center_api_key: str = ""
    # 관리자 대시보드 전용 계정. 회원가입 폼을 거치지 않고 앱 시작 시 자동으로
    # 생성된다(app.auth.service.seed_admin_user 참고) — 이 이메일과 일치하는
    # 사용자만 /admin/* 엔드포인트에 접근할 수 있다(require_admin).
    admin_email: str = "admin@naver.com"
    admin_password: str = "admin123!"

    model_config = {"env_file": ".env"}

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
