"""Plan API endpoint (API-compatible)."""

from fastapi import APIRouter

from app.models.schemas import PlanConfirmRequest, PlanConfirmResponse, ApplicationPayload
from app.services.session_manager import session_manager


router = APIRouter(prefix="/api/plan", tags=["plan"])


@router.post("/confirm", response_model=PlanConfirmResponse)
async def confirm_plan(request: PlanConfirmRequest) -> PlanConfirmResponse:
    try:
        plan = session_manager.get_plan(request.session_id, request.plan_id)
        if not plan:
            return PlanConfirmResponse(status="error", error_message="指定されたプランが見つかりません。")

        session = session_manager.get_session(request.session_id)
        purpose = request.purpose or (session.conditions.purpose if session else None) or "商談"

        transportation_cost = 0
        transportation_desc = ""
        if plan.outbound_transportation:
            transportation_cost += plan.outbound_transportation.price
            transportation_desc = (
                f"{plan.outbound_transportation.type}"
                f"({plan.outbound_transportation.departure_station}->{plan.outbound_transportation.arrival_station})"
            )
        if plan.return_transportation:
            transportation_cost += plan.return_transportation.price
            transportation_desc += " 往復"

        hotel_cost = 0
        hotel_desc = ""
        if plan.hotel:
            hotel_cost = plan.hotel.total_price
            hotel_desc = f"{plan.hotel.name} {plan.hotel.nights}泊"

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
            notes=f"社内旅費規程: {plan.summary.policy_status}"
            + (f" - {plan.summary.policy_note}" if plan.summary.policy_note else ""),
        )

        return PlanConfirmResponse(status="confirmed", application_payload=application_payload)
    except Exception as e:
        return PlanConfirmResponse(status="error", error_message=f"プラン確定処理中にエラーが発生しました: {str(e)}")

