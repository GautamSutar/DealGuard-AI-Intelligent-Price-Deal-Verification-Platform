from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel


class ChatRequest(BaseModel):
    session_id: str
    message: str
    product_id: Optional[str] = None  # optional product context


class ChatSource(BaseModel):
    type: str  # "price_history" | "current_price" | "analysis"
    marketplace: Optional[str] = None
    description: str


class ChatResponse(BaseModel):
    session_id: str
    message: str  # human-readable AI response
    data: Optional[Dict[str, Any]] = None  # structured price data used
    sources: List[ChatSource] = []
    tool_calls_made: List[str] = []  # transparency: which tools the agent called
