"""チャットAPIエンドポイント"""
import time
from fastapi import APIRouter, HTTPException

from app.models.schemas import ChatRequest, ChatResponse, Message
from app.services.session_manager import session_manager
from app.agents import TravelSupportAgent
from app.logging_config import get_logger

router = APIRouter(prefix="/api/chat", tags=["chat"])
logger = get_logger(__name__)

# エージェントのシングルトン
_agent: TravelSupportAgent = None


def get_agent() -> TravelSupportAgent:
    """エージェントを取得"""
    global _agent
    if _agent is None:
        logger.info("agent_initialization", message="Creating new TravelSupportAgent instance")
        _agent = TravelSupportAgent()
        logger.info("agent_initialized", message="TravelSupportAgent created successfully")
    return _agent


@router.post("", response_model=ChatResponse)
async def send_message(request: ChatRequest) -> ChatResponse:
    """チャットメッセージを送信"""
    start_time = time.time()
    
    logger.info(
        "chat_request_received",
        user_id=request.user_id,
        session_id=request.session_id,
        message_length=len(request.message),
        message_preview=request.message[:100] + "..." if len(request.message) > 100 else request.message,
    )
    
    try:
        # セッションを取得または作成
        logger.debug(
            "session_lookup",
            session_id=request.session_id,
            user_id=request.user_id,
        )
        
        session = session_manager.get_or_create_session(
            request.session_id,
            request.user_id,
        )
        
        logger.debug(
            "session_resolved",
            session_id=session.session_id,
            is_new_session=request.session_id is None or request.session_id != session.session_id,
            existing_message_count=len(session.messages),
            existing_plan_count=len(session.plans),
        )
        
        # ユーザーメッセージを追加
        user_message = Message(
            role="user",
            type="text",
            content=request.message,
        )
        session_manager.update_session(
            session.session_id,
            add_message=user_message,
        )
        logger.debug(
            "user_message_added",
            session_id=session.session_id,
            message_role="user",
        )
        
        # エージェントで処理
        logger.info(
            "agent_processing_start",
            session_id=session.session_id,
        )
        
        agent_start = time.time()
        agent = get_agent()
        result = await agent.process_message(
            user_message=request.message,
            session_data=session,
        )
        agent_duration = time.time() - agent_start
        
        logger.info(
            "agent_processing_complete",
            session_id=session.session_id,
            duration_ms=round(agent_duration * 1000, 2),
            response_length=len(result.get("response", "")),
        )
        
        # 条件を更新
        updated_conditions = result.get("updated_conditions")
        if updated_conditions:
            logger.debug(
                "conditions_updated",
                session_id=session.session_id,
                departure_location=updated_conditions.departure_location,
                destination=updated_conditions.destination,
                depart_date=updated_conditions.depart_date,
                return_date=updated_conditions.return_date,
                budget=updated_conditions.budget,
                preferred_transportation=updated_conditions.preferred_transportation,
            )
            session_manager.update_session(
                session.session_id,
                conditions=updated_conditions,
            )
        
        # 条件が揃っていればプランを生成
        updated_session = session_manager.get_session(session.session_id)
        plans = []
        
        conditions = updated_session.conditions
        conditions_complete = all([
            conditions.departure_location,
            conditions.destination,
            conditions.depart_date,
            conditions.return_date,
        ])
        
        logger.debug(
            "conditions_check",
            session_id=session.session_id,
            conditions_complete=conditions_complete,
            has_departure=bool(conditions.departure_location),
            has_destination=bool(conditions.destination),
            has_depart_date=bool(conditions.depart_date),
            has_return_date=bool(conditions.return_date),
        )
        
        if conditions_complete:
            # プラン生成
            logger.info(
                "plan_generation_start",
                session_id=session.session_id,
                departure=conditions.departure_location,
                destination=conditions.destination,
                depart_date=conditions.depart_date,
                return_date=conditions.return_date,
                budget=conditions.budget,
            )
            
            plan_start = time.time()
            plans = await agent.generate_plans(conditions)
            plan_duration = time.time() - plan_start
            
            session_manager.add_plans(session.session_id, plans)
            
            logger.info(
                "plan_generation_complete",
                session_id=session.session_id,
                plan_count=len(plans),
                duration_ms=round(plan_duration * 1000, 2),
                plan_labels=[p.label for p in plans],
            )
            
            for plan in plans:
                logger.debug(
                    "plan_detail",
                    session_id=session.session_id,
                    plan_id=plan.plan_id,
                    label=plan.label,
                    destination=plan.summary.destination,
                    estimated_total=plan.summary.estimated_total,
                    policy_status=plan.summary.policy_status,
                )
        
        # アシスタントメッセージを追加
        assistant_message = Message(
            role="assistant",
            type="plan_cards" if plans else "text",
            content=result.get("response", ""),
        )
        session_manager.update_session(
            session.session_id,
            add_message=assistant_message,
        )
        
        logger.debug(
            "assistant_message_added",
            session_id=session.session_id,
            message_type=assistant_message.type,
            has_plans=len(plans) > 0,
        )
        
        total_duration = time.time() - start_time
        logger.info(
            "chat_response_sent",
            session_id=session.session_id,
            total_duration_ms=round(total_duration * 1000, 2),
            plan_count=len(plans),
            response_type=assistant_message.type,
        )
        
        return ChatResponse(
            session_id=session.session_id,
            messages=[assistant_message],
            plans=plans,
        )
        
    except Exception as e:
        logger.error(
            "chat_processing_error",
            user_id=request.user_id,
            session_id=request.session_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    """セッション情報を取得"""
    logger.debug(
        "session_get_request",
        session_id=session_id,
    )
    
    session = session_manager.get_session(session_id)
    if not session:
        logger.warning(
            "session_not_found",
            session_id=session_id,
        )
        raise HTTPException(status_code=404, detail="Session not found")
    
    logger.debug(
        "session_retrieved",
        session_id=session_id,
        message_count=len(session.messages),
        plan_count=len(session.plans),
    )
    
    return {
        "session_id": session.session_id,
        "user_id": session.user_id,
        "conditions": session.conditions,
        "message_count": len(session.messages),
        "plan_count": len(session.plans),
        "created_at": session.created_at,
        "updated_at": session.updated_at,
    }
