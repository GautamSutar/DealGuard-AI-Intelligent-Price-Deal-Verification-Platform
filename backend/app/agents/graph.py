"""
DealGuard AI agent — agentic loop with Groq tool calling.

Flow:
  User message
    → LLM decides which tools to call
    → Tools query PostgreSQL / price engine (never the LLM itself)
    → LLM receives structured results
    → LLM generates a human-readable explanation
    → Response returned to user

The LLM is NEVER the source of price data. If a tool returns no data,
the LLM must say "data unavailable" — it must not fill in the gap.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools import TOOL_DEFINITIONS, execute_tool
from app.providers.llm.groq.groq_provider import SYSTEM_PROMPT, get_groq_provider
from app.schemas.chat import ChatResponse, ChatSource

logger = structlog.get_logger(__name__)

MAX_TOOL_ROUNDS = 5  # Prevent infinite loops


async def run_agent(
    db: AsyncSession,
    session_id: str,
    user_message: str,
    conversation_history: List[Dict[str, Any]],
    product_id: Optional[str] = None,
) -> ChatResponse:
    """
    Run one turn of the DealGuard agent loop.

    Returns a ChatResponse with the LLM explanation and the structured
    data that was used to generate it.
    """
    llm = get_groq_provider()
    messages = list(conversation_history)
    messages.append({"role": "user", "content": user_message})

    tool_calls_made: List[str] = []
    data_used: Dict[str, Any] = {}
    sources: List[ChatSource] = []

    for _ in range(MAX_TOOL_ROUNDS):
        response = await llm.chat_with_tools(
            messages=messages,
            tools=TOOL_DEFINITIONS,
            system_prompt=SYSTEM_PROMPT,
        )

        if "error" in response:
            return ChatResponse(
                session_id=session_id,
                message="I encountered an error communicating with the AI service. Please try again.",
                sources=[],
            )

        choice = response.get("choices", [{}])[0]
        finish_reason = choice.get("finish_reason", "stop")
        message = choice.get("message", {})

        # Add assistant message to history
        messages.append({"role": "assistant", "content": message.get("content") or "", "tool_calls": message.get("tool_calls")})

        if finish_reason == "tool_calls" and message.get("tool_calls"):
            for tool_call in message["tool_calls"]:
                fn = tool_call.get("function", {})
                tool_name = fn.get("name", "")
                try:
                    tool_args = json.loads(fn.get("arguments", "{}"))
                except json.JSONDecodeError:
                    tool_args = {}

                tool_calls_made.append(tool_name)
                result = await execute_tool(tool_name, tool_args, db)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.get("id", ""),
                    "content": result,
                })

                # Track data provenance for ChatResponse
                try:
                    parsed = json.loads(result)
                    data_used[tool_name] = parsed
                    sources.append(ChatSource(
                        type=tool_name,
                        description=f"Retrieved via {tool_name}",
                    ))
                except Exception:
                    pass

        else:
            # LLM finished without more tool calls
            final_text = message.get("content") or "I could not generate a response."

            # Extract key price figures for the structured data field
            structured = _extract_structured_data(data_used)

            return ChatResponse(
                session_id=session_id,
                message=final_text,
                data=structured,
                sources=sources,
                tool_calls_made=tool_calls_made,
            )

    return ChatResponse(
        session_id=session_id,
        message="The analysis took too many steps. Please try a more specific query.",
        sources=sources,
    )


def _extract_structured_data(data_used: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Pull key numbers from tool results for the structured data field."""
    result: Dict[str, Any] = {}

    analysis = data_used.get("get_price_analysis")
    if analysis and isinstance(analysis, dict):
        for key in ("current_price", "current_effective_price", "historical_average",
                    "historical_minimum", "historical_maximum", "pct_vs_average",
                    "classification", "history_coverage_days", "price_trend"):
            if key in analysis:
                result[key] = analysis[key]

    return result if result else None
