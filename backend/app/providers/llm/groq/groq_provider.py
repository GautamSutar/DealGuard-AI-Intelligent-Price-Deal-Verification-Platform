"""
Groq LLM provider implementation.

The LLM is the EXPLANATION LAYER only. It never invents price data.
All numbers it quotes must come from backend tool results.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import structlog

from app.config import settings
from app.providers.llm.base import LLMProvider

logger = structlog.get_logger(__name__)


SYSTEM_PROMPT = """You are DealGuard, an Indian e-commerce price analysis assistant.
Rules: Only use data from tools. Never invent prices. If no data, say "data unavailable."
Format: Identify product, show price vs history, state classification (GOOD_DEAL/FAIR/OVERPRICED), end with "The final purchasing decision is yours."
Be factual and neutral. Disclose data coverage."""


class GroqProvider(LLMProvider):
    def __init__(self):
        try:
            from groq import AsyncGroq
            self._client = AsyncGroq(api_key=settings.groq_api_key)
            self._model = settings.llm_model
        except ImportError:
            logger.error("groq package not installed")
            self._client = None

    @property
    def provider_name(self) -> str:
        return "groq"

    async def chat_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        system_prompt: str = SYSTEM_PROMPT,
    ) -> Dict[str, Any]:
        if not self._client:
            return {"error": "Groq client not initialised. Check GROQ_API_KEY."}

        full_messages = [{"role": "system", "content": system_prompt}] + messages

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=full_messages,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None,
                temperature=0.1,  # Low temperature for factual, consistent responses
                max_tokens=2048,
            )
            return response.model_dump()
        except Exception as exc:
            logger.error("Groq API error", error=str(exc))
            return {"error": str(exc)}


def get_groq_provider() -> LLMProvider:
    return GroqProvider()
