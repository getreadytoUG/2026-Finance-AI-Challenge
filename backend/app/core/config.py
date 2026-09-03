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
    # 소셜 로그인(카카오) OAuth 자격 증명. 값이 비어 있으면
    # /auth/kakao/login 엔드포인트가 503을 돌려준다(설정 안 됨). 운영에서는
    # Cloudtype 환경 변수로 주입한다 — .env.example / README 참고.
    kakao_client_id: str = ""
    kakao_client_secret: str = ""  # 카카오는 "보안" 사용 설정 시에만 필요, 아니면 빈 값
    # OAuth 콜백 URL. 프로바이더 콘솔에 등록한 값과 정확히 일치해야 한다.
    # 로컬 기본값이며, 배포 환경에서는 배포된 백엔드 주소로 덮어쓴다.
    kakao_redirect_uri: str = "http://localhost:8000/auth/kakao/callback"
    # 소셜 로그인 성공 후 토큰을 들고 돌아갈 프론트엔드 주소.
    frontend_base_url: str = "http://localhost:3000"
    # 관리자 대시보드 전용 계정. 회원가입 폼을 거치지 않고 앱 시작 시 자동으로
    # 생성된다(app.auth.service.seed_admin_user 참고) — 이 이메일과 일치하는
    # 사용자만 /admin/* 엔드포인트에 접근할 수 있다(require_admin).
    admin_email: str = "admin@naver.com"
    admin_password: str = "admin123!"

    # extra="ignore": .env나 배포 환경에 이 모델이 모르는 변수(예: 제거된
    # NAVER_CLIENT_ID)가 남아 있어도 기동이 깨지지 않게 무시한다.
    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
