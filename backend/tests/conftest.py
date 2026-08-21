import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.core.db import Base, get_db
from app.main import app
from app.features.policy_matcher.youth_center_client import RawYouthPolicy


@pytest.fixture(autouse=True)
def mock_fetch_policies(monkeypatch):
    """Mock fetch_policies to return a test policy for integration tests."""
    def _fetch_policies(query=None, page_index=1, display=100):
        return [
            RawYouthPolicy(
                policy_name="청년 전세자금대출 (테스트)",
                description="전세자금을 지원합니다",
                apply_url="https://www.example.com",
                application_period="상시",
                min_age=None,
                max_age=None,
                min_income_krw=None,
                max_income_krw=None,
                marital_status="",
                region_code="",
            )
        ]

    monkeypatch.setattr("app.features.policy_matcher.tool.fetch_policies", _fetch_policies)


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
