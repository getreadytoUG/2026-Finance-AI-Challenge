from app.core.config import settings
from app.llm.base import LLMProvider
from app.llm.claude_provider import ClaudeProvider
from app.llm.openai_provider import OpenAIProvider


def get_provider() -> LLMProvider:
    if settings.llm_provider == "claude":
        return ClaudeProvider()
    if settings.llm_provider == "openai":
        return OpenAIProvider()
    raise ValueError(f"Unknown LLM_PROVIDER: {settings.llm_provider}")
