"""
Grok (xAI) LLM provider.

xAI's API is OpenAI-compatible:
  Base URL : https://api.x.ai/v1
  Models   : grok-3, grok-3-mini, grok-2-1212
  Auth     : Bearer token (GROK_API_KEY env var)
  SDK      : openai Python package with custom base_url

The LLM is the EXPLANATION layer only. It never generates price data.
All figures it quotes must come from backend tool results.
"""

from __future__ import annotations

from typing import Any, Dict, List

import structlog

from app.config import settings
from app.providers.llm.base import LLMProvider

logger = structlog.get_logger(__name__)

# Identical system prompt to Groq provider — behaviour must not change
# when switching providers.
SYSTEM_PROMPT = """You are DealGuard, an Indian e-commerce price analysis assistant.
Rules: Only use data from tools. Never invent prices. If no data, say "data unavailable."
Format: Identify product, show price vs history, state classification (GOOD_DEAL/FAIR/OVERPRICED), end with "The final purchasing decision is yours."
Be factual and neutral. Disclose data coverage."""

_XAI_BASE_URL = "https://api.x.ai/v1"


class GrokProvider(LLMProvider):
    """
    LLM provider backed by xAI's Grok via OpenAI-compatible API.
    Drop-in replacement for GroqProvider — same interface, same system prompt.
    """

    def __init__(self):
        try:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(
                api_key=settings.grok_api_key,
                base_url=_XAI_BASE_URL,
            )
            self._model = settings.grok_model
            logger.info("Grok provider initialised", model=self._model)
        except ImportError:
            logger.error(
                "openai package not installed — run: pip install openai"
            )
            self._client = None

    @property
    def provider_name(self) -> str:
        return "grok"

    async def chat_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        system_prompt: str = SYSTEM_PROMPT,
    ) -> Dict[str, Any]:
        if not self._client:
            return {
                "error": (
                    "Grok client not initialised. "
                    "Check GROK_API_KEY and that openai is installed."
                )
            }

        full_messages = (
            [{"role": "system", "content": system_prompt}] + messages
        )

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=full_messages,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None,
                temperature=0.1,
                max_tokens=2048,
            )
            return response.model_dump()
        except Exception as exc:
            logger.error("Grok API error", error=str(exc))
            return {"error": str(exc)}


def get_grok_provider() -> LLMProvider:
    return GrokProvider()
