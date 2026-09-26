"""
LLM provider factory.

Selects the LLM backend based on LLM_PROVIDER env var:
  grok  — xAI Grok (requires GROK_API_KEY)
  groq  — Groq inference (requires GROQ_API_KEY)

Defaults to grok when LLM_PROVIDER=grok (recommended).
"""

from __future__ import annotations

import structlog

from app.config import settings
from app.providers.llm.base import LLMProvider

logger = structlog.get_logger(__name__)


def get_llm_provider() -> LLMProvider:
    provider = settings.llm_provider.lower()

    if provider == "grok":
        if not settings.grok_api_key:
            logger.warning(
                "GROK_API_KEY not set — falling back to Groq"
            )
        else:
            from app.providers.llm.grok.grok_provider import GrokProvider
            return GrokProvider()

    if provider == "groq" or not settings.grok_api_key:
        if not settings.groq_api_key:
            logger.warning(
                "Neither GROK_API_KEY nor GROQ_API_KEY set — "
                "AI chat will return errors"
            )
        from app.providers.llm.groq.groq_provider import GroqProvider
        return GroqProvider()

    logger.warning(
        "Unknown LLM_PROVIDER, defaulting to Groq",
        provider=provider,
    )
    from app.providers.llm.groq.groq_provider import GroqProvider
    return GroqProvider()


def get_system_prompt() -> str:
    """Return the system prompt for the active LLM provider."""
    provider = settings.llm_provider.lower()
    if provider == "grok":
        from app.providers.llm.grok.grok_provider import SYSTEM_PROMPT
    else:
        from app.providers.llm.groq.groq_provider import SYSTEM_PROMPT
    return SYSTEM_PROMPT
