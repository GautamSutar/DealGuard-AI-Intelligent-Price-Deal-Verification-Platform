import json
from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graph import run_agent
from app.database import get_db
from app.models.agent_session import AgentMessage, AgentSession
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Conversational AI endpoint.

    The AI agent calls backend tools (search, history, analysis) to answer
    the user's question. It NEVER invents price data. If data is unavailable,
    it will say so explicitly.

    Example questions:
    - "Is iPhone 16 currently cheap?"
    - "Compare this product with its historical price"
    - "Was this product cheaper last month?"
    - "Show me the lowest price in the last 50 weeks"
    - "Is this discount actually significant?"
    """
    # Get or create session
    session_result = await db.execute(
        select(AgentSession).where(AgentSession.session_id == request.session_id)
    )
    session = session_result.scalar_one_or_none()
    if not session:
        session = AgentSession(session_id=request.session_id)
        db.add(session)
        await db.commit()

    # Load conversation history
    history_result = await db.execute(
        select(AgentMessage)
        .where(AgentMessage.session_id == request.session_id)
        .order_by(AgentMessage.created_at.asc())
        .limit(20)
    )
    history_rows = history_result.scalars().all()

    conversation_history: List[Dict[str, Any]] = []
    for row in history_rows:
        msg: Dict[str, Any] = {"role": row.role, "content": row.content}
        if row.tool_calls:
            try:
                msg["tool_calls"] = json.loads(row.tool_calls)
            except Exception:
                pass
        conversation_history.append(msg)

    # Run agent
    response = await run_agent(
        db=db,
        session_id=request.session_id,
        user_message=request.message,
        conversation_history=conversation_history,
        product_id=request.product_id,
    )

    # Persist user message and assistant response
    db.add(AgentMessage(session_id=request.session_id, role="user", content=request.message))
    db.add(AgentMessage(session_id=request.session_id, role="assistant", content=response.message))
    await db.commit()

    return response
