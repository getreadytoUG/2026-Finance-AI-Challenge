import pytest

from app.llm.claude_provider import ClaudeProvider
from app.llm.factory import get_provider
from app.llm.openai_provider import OpenAIProvider


def test_get_provider_returns_claude_by_default(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.llm_provider", "claude")
    monkeypatch.setattr("app.core.config.settings.anthropic_api_key", "test-key")
    provider = get_provider()
    assert isinstance(provider, ClaudeProvider)


def test_get_provider_returns_openai_when_configured(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.llm_provider", "openai")
    monkeypatch.setattr("app.core.config.settings.openai_api_key", "test-key")
    provider = get_provider()
    assert isinstance(provider, OpenAIProvider)


def test_get_provider_raises_on_unknown_provider(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.llm_provider", "not-a-real-provider")
    with pytest.raises(ValueError):
        get_provider()
