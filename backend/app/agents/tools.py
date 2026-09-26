"""
DealGuard agent tools — the only way the LLM can access price data.

DESIGN PRINCIPLE:
  The LLM is not allowed to invent data. Every number it presents to the user
  must come from one of these tool functions, which in turn query the database
  or the price engine. The tool definitions below match the Groq/OpenAI
  function-calling format.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.analysis_service import get_or_calculate_analysis
from app.services.history_service import bootstrap_history, get_price_history
from app.services.offer_service import calculate_effective_price_breakdown, get_listing_offers
from app.services.product_service import search_products

logger = structlog.get_logger(__name__)

# ── Tool definitions (sent to the LLM) ──────────────────────────────────────

TOOL_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "Search for products by name or marketplace URL. Returns a list of matching products with current prices.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Product name or Amazon/Flipkart URL"},
                    "marketplace": {"type": "string", "description": "Filter by marketplace: 'amazon' or 'flipkart'", "enum": ["amazon", "flipkart"]},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_price_history",
            "description": "Retrieve historical price data for a product listing. Required before any historical comparison.",
            "parameters": {
                "type": "object",
                "properties": {
                    "listing_id": {"type": "string", "description": "UUID of the product listing"},
                    "days": {"type": "integer", "description": "Number of days of history (7-365)", "default": 365},
                },
                "required": ["listing_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_price_analysis",
            "description": "Get the complete price analysis with historical statistics (average, median, min, max, trend, classification). Always call this after get_price_history.",
            "parameters": {
                "type": "object",
                "properties": {
                    "listing_id": {"type": "string", "description": "UUID of the product listing"},
                },
                "required": ["listing_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_offers",
            "description": "Retrieve all current offers and discounts for a product listing, including conditional offers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "listing_id": {"type": "string", "description": "UUID of the product listing"},
                },
                "required": ["listing_id"],
            },
        },
    },
]

# ── Tool execution ───────────────────────────────────────────────────────────

async def execute_tool(
    tool_name: str,
    tool_args: Dict[str, Any],
    db: AsyncSession,
) -> str:
    """Dispatch a tool call and return the result as a JSON string."""
    logger.info("Agent tool call", tool=tool_name, args=tool_args)

    try:
        if tool_name == "search_products":
            results = await search_products(db, tool_args["query"], tool_args.get("marketplace"))
            return json.dumps([r.model_dump(mode="json") for r in results])

        elif tool_name == "get_price_history":
            listing_id = UUID(tool_args["listing_id"])
            days = tool_args.get("days", 365)
            points = await get_price_history(db, listing_id, days)
            # Return compact summary: first 5 + last 25 points to stay within token limits
            sample = points[:5] + points[-25:] if len(points) > 30 else points
            return json.dumps({
                "total_points": len(points),
                "days_requested": days,
                "sample_points": [p.model_dump() for p in sample],
            })

        elif tool_name == "get_price_analysis":
            listing_id = UUID(tool_args["listing_id"])
            from app.models.listing import ProductListing
            listing = await db.get(ProductListing, listing_id)
            if listing:
                await bootstrap_history(db, listing)
            result = await get_or_calculate_analysis(db, listing_id, force_recalculate=True)
            if result:
                return json.dumps(result.model_dump(mode="json"))
            return json.dumps({"error": "Analysis could not be generated. Insufficient data."})

        elif tool_name == "get_current_offers":
            listing_id = UUID(tool_args["listing_id"])
            offers = await get_listing_offers(db, listing_id)
            return json.dumps([o.model_dump(mode="json") for o in offers])

        else:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})

    except Exception as exc:
        logger.error("Tool execution failed", tool=tool_name, error=str(exc))
        return json.dumps({"error": f"Tool '{tool_name}' failed: {str(exc)}"})
