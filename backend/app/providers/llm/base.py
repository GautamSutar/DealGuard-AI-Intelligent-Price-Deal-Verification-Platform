"""Base abstraction for LLM providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class LLMProvider(ABC):
    """
    The LLM is the explanation layer only.
    It calls backend tools — it never generates price data.
    """

    @abstractmethod
    async def chat_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        system_prompt: str,
    ) -> Dict[str, Any]:
        """
        Run one turn of a tool-calling conversation.
        Returns the raw provider response for the caller to parse.
        """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Short identifier: 'groq' | 'openai' etc."""
