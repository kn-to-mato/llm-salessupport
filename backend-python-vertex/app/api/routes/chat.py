"""Chat API endpoint (API-compatible)."""

from fastapi import APIRouter, HTTPException

from app.models.schemas import ChatRequest, ChatResponse, Message
from app.services.session_manager import session_manager
from app.agents.travel_agent import TravelSupportAgent


router = APIRouter(prefix="/api/chat", tags=["chat"])
_agent: TravelSupportAgent | None = None


def get_agent() -> TravelSupportAgent:
    global _agent
    if _agent is None:
        _agent = TravelSupportAgent()
    return _agent


@router.post("", response_model=ChatResponse)
async def send_message(request: ChatRequest) -> ChatResponse:
    try:
        session = session_manager.get_or_create_session(request.session_id, request.user_id)

        # store user message
        session_manager.update_session(
            session.session_id,
            add_message=Message(role="user", type="text", content=request.message),
        )

        agent = get_agent()
        result = await agent.process_message(
            user_message=request.message,
            session_data=session,
        )

        plans = result.get("plans", []) or []
        if plans:
            session_manager.add_plans(session.session_id, plans)

        assistant_message = Message(
            role="assistant",
            type="plan_cards" if plans else "text",
            content=result.get("response", ""),
        )
        session_manager.update_session(session.session_id, add_message=assistant_message)

        return ChatResponse(
            session_id=session.session_id,
            messages=[assistant_message],
            plans=plans,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

