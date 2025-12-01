"""プランAPIエンドポイント"""
import time
from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    PlanConfirmRequest,
    PlanConfirmResponse,
    ApplicationPayload,
)
from app.services.session_manager import session_manager
from app.logging_config import get_logger

router = APIRouter(prefix="/api/plan", tags=["plan"])
logger = get_logger(__name__)


@router.post("/confirm", response_model=PlanConfirmResponse)
async def confirm_plan(request: PlanConfirmRequest) -> PlanConfirmResponse:
    """プランを確定して申請データを生成"""
    start_time = time.time()
    
    logger.info(
        "plan_confirm_request_received",
        user_id=request.user_id,
        session_id=request.session_id,
        plan_id=request.plan_id,
        purpose=request.purpose,
    )
    
    try:
        # セッションからプランを取得
        logger.debug(
            "plan_lookup",
            session_id=request.session_id,
            plan_id=request.plan_id,
        )
        
        plan = session_manager.get_plan(request.session_id, request.plan_id)
        
        if not plan:
            logger.warning(
                "plan_not_found",
                session_id=request.session_id,
                plan_id=request.plan_id,
            )
            return PlanConfirmResponse(
                status="error",
                error_message="指定されたプランが見つかりません。",
            )
        
        logger.debug(
            "plan_found",
            plan_id=plan.plan_id,
            label=plan.label,
            destination=plan.summary.destination,
            estimated_total=plan.summary.estimated_total,
        )
        
        # セッションから追加情報を取得
        session = session_manager.get_session(request.session_id)
        purpose = request.purpose or session.conditions.purpose or "商談"
        
        logger.debug(
            "purpose_resolved",
            session_id=request.session_id,
            purpose=purpose,
            source="request" if request.purpose else ("session" if session.conditions.purpose else "default"),
        )
        
        # 交通費を計算
        transportation_cost = 0
        transportation_desc = ""
        if plan.outbound_transportation:
            transportation_cost += plan.outbound_transportation.price
            transportation_desc = f"{plan.outbound_transportation.type}({plan.outbound_transportation.departure_station}->{plan.outbound_transportation.arrival_station})"
            logger.debug(
                "outbound_transportation",
                type=plan.outbound_transportation.type,
                departure=plan.outbound_transportation.departure_station,
                arrival=plan.outbound_transportation.arrival_station,
                price=plan.outbound_transportation.price,
            )
        if plan.return_transportation:
            transportation_cost += plan.return_transportation.price
            transportation_desc += " 往復"
            logger.debug(
                "return_transportation",
                type=plan.return_transportation.type,
                departure=plan.return_transportation.departure_station,
                arrival=plan.return_transportation.arrival_station,
                price=plan.return_transportation.price,
            )
        
        logger.debug(
            "transportation_cost_calculated",
            total_cost=transportation_cost,
            description=transportation_desc,
        )
        
        # 宿泊費を計算
        hotel_cost = 0
        hotel_desc = ""
        if plan.hotel:
            hotel_cost = plan.hotel.total_price
            hotel_desc = f"{plan.hotel.name} {plan.hotel.nights}泊"
            logger.debug(
                "hotel_cost",
                name=plan.hotel.name,
                nights=plan.hotel.nights,
                price_per_night=plan.hotel.price_per_night,
                total_price=hotel_cost,
            )
        
        # 申請データを生成
        application_payload = ApplicationPayload(
            destination=plan.summary.destination,
            depart_date=plan.summary.depart_date,
            return_date=plan.summary.return_date,
            purpose=purpose,
            transportation=transportation_desc,
            transportation_cost=transportation_cost,
            hotel=hotel_desc,
            hotel_cost=hotel_cost,
            total_budget=plan.summary.estimated_total,
            notes=f"社内旅費規程: {plan.summary.policy_status}" + 
                  (f" - {plan.summary.policy_note}" if plan.summary.policy_note else ""),
        )
        
        duration_ms = (time.time() - start_time) * 1000
        
        logger.info(
            "plan_confirmed",
            session_id=request.session_id,
            plan_id=plan.plan_id,
            label=plan.label,
            destination=application_payload.destination,
            depart_date=application_payload.depart_date,
            return_date=application_payload.return_date,
            transportation_cost=application_payload.transportation_cost,
            hotel_cost=application_payload.hotel_cost,
            total_budget=application_payload.total_budget,
            duration_ms=round(duration_ms, 2),
        )
        
        return PlanConfirmResponse(
            status="confirmed",
            application_payload=application_payload,
        )
        
    except Exception as e:
        logger.error(
            "plan_confirm_error",
            user_id=request.user_id,
            session_id=request.session_id,
            plan_id=request.plan_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        return PlanConfirmResponse(
            status="error",
            error_message=f"プラン確定処理中にエラーが発生しました: {str(e)}",
        )


@router.get("/{session_id}")
async def get_plans(session_id: str):
    """セッションのプラン一覧を取得"""
    logger.debug(
        "plans_list_request",
        session_id=session_id,
    )
    
    session = session_manager.get_session(session_id)
    if not session:
        logger.warning(
            "session_not_found_for_plans",
            session_id=session_id,
        )
        raise HTTPException(status_code=404, detail="Session not found")
    
    logger.debug(
        "plans_retrieved",
        session_id=session_id,
        plan_count=len(session.plans),
    )
    
    return {
        "session_id": session_id,
        "plans": [plan.model_dump() for plan in session.plans],
    }


@router.get("/{session_id}/{plan_id}")
async def get_plan(session_id: str, plan_id: str):
    """特定のプランを取得"""
    logger.debug(
        "plan_get_request",
        session_id=session_id,
        plan_id=plan_id,
    )
    
    plan = session_manager.get_plan(session_id, plan_id)
    if not plan:
        logger.warning(
            "plan_not_found_for_get",
            session_id=session_id,
            plan_id=plan_id,
        )
        raise HTTPException(status_code=404, detail="Plan not found")
    
    logger.debug(
        "plan_retrieved",
        session_id=session_id,
        plan_id=plan_id,
        label=plan.label,
    )
    
    return plan.model_dump()
