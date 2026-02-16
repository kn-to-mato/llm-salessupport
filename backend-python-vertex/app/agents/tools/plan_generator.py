"""Trip plan generator tool (mock).

Important: This tool internally calls transportation_search and hotel_search (same as existing spec).
"""

from typing import Any, Dict, Optional
import uuid
from datetime import datetime

from pydantic import BaseModel, Field
from vertexai.generative_models import FunctionDeclaration

from .transportation_search import run_transportation_search
from .hotel_search import run_hotel_search


class PlanGeneratorInput(BaseModel):
    departure_location: str = Field(..., description="出発地（例: 東京）")
    destination: str = Field(..., description="目的地（例: 大阪）")
    depart_date: str = Field(..., description="出発日（YYYY-MM-DD）")
    return_date: Optional[str] = Field(None, description="帰着日（YYYY-MM-DD、日帰りなら省略可）")
    budget: Optional[int] = Field(None, description="予算上限（円）")
    preferred_transportation: Optional[str] = Field(None, description="希望交通手段（新幹線、飛行機など）")


def _calc_nights(depart_date: str, return_date: Optional[str]) -> int:
    if not return_date:
        return 0
    try:
        dep = datetime.strptime(depart_date, "%Y-%m-%d")
        ret = datetime.strptime(return_date, "%Y-%m-%d")
        return max(0, (ret - dep).days)
    except Exception:
        return 1


def run_plan_generator(**kwargs) -> Dict[str, Any]:
    params = PlanGeneratorInput(**kwargs)

    trans_result = run_transportation_search(
        departure=params.departure_location,
        destination=params.destination,
        preferred_type=params.preferred_transportation,
    )
    transportation_options = trans_result.get("options", [])

    is_day_trip = params.return_date is None
    nights = _calc_nights(params.depart_date, params.return_date)

    hotel_options = []
    if not is_day_trip and nights > 0:
        hotel_result = run_hotel_search(
            destination=params.destination,
            nights=nights,
            max_price_per_night=15000,
        )
        hotel_options = hotel_result.get("hotels", [])

    plans = []
    plan_labels = ["A", "B", "C", "D", "E"]
    plan_count = 0

    def budget_note(total: int) -> tuple[str, Optional[str]]:
        if params.budget and total > params.budget:
            return "注意", f"予算 {params.budget:,}円を{total - params.budget:,}円超過しています"
        return "OK", None

    if is_day_trip:
        for trans in transportation_options[:3]:
            if plan_count >= 3:
                break
            schedule = trans.get("schedules", [{}])[0] if trans.get("schedules") else {}
            trans_price = schedule.get("price", trans.get("price", 0))
            total = trans_price * 2
            policy_status, policy_note = budget_note(total)

            plans.append(
                {
                    "plan_id": str(uuid.uuid4()),
                    "label": f"プラン{plan_labels[plan_count]}",
                    "summary": {
                        "depart_date": params.depart_date,
                        "return_date": params.depart_date,
                        "destination": params.destination,
                        "transportation": f"{trans.get('type', '交通手段')}（{trans.get('train_name', '')}）",
                        "hotel": "なし（日帰り）",
                        "estimated_total": total,
                        "policy_status": policy_status,
                        "policy_note": policy_note,
                    },
                    "outbound_transportation": {
                        "type": trans.get("type", ""),
                        "departure_station": trans.get("departure_station", ""),
                        "arrival_station": trans.get("arrival_station", ""),
                        "departure_time": schedule.get("departure", ""),
                        "arrival_time": schedule.get("arrival", ""),
                        "price": trans_price,
                        "train_name": trans.get("train_name", ""),
                    },
                    "return_transportation": {
                        "type": trans.get("type", ""),
                        "departure_station": trans.get("arrival_station", ""),
                        "arrival_station": trans.get("departure_station", ""),
                        "departure_time": "18:00",
                        "arrival_time": "",
                        "price": trans_price,
                        "train_name": trans.get("train_name", ""),
                    },
                    "hotel": None,
                }
            )
            plan_count += 1
    else:
        for trans in transportation_options[:3]:
            for hotel in hotel_options[:2]:
                if plan_count >= 3:
                    break
                schedule = trans.get("schedules", [{}])[0] if trans.get("schedules") else {}
                trans_price = schedule.get("price", trans.get("price", 0))
                round_trip = trans_price * 2
                hotel_price = hotel.get("price_per_night", 0) * nights
                total = round_trip + hotel_price

                policy_status, policy_note = budget_note(total)
                if hotel.get("price_per_night", 0) > 15000:
                    policy_status, policy_note = "NG", "宿泊費が規程上限（15,000円/泊）を超過しています"

                plans.append(
                    {
                        "plan_id": str(uuid.uuid4()),
                        "label": f"プラン{plan_labels[plan_count]}",
                        "summary": {
                            "depart_date": params.depart_date,
                            "return_date": params.return_date or "",
                            "destination": params.destination,
                            "transportation": f"{trans.get('type', '交通手段')}（{trans.get('train_name', '')}）",
                            "hotel": f"{hotel.get('name', 'ホテル')} {nights}泊",
                            "estimated_total": total,
                            "policy_status": policy_status,
                            "policy_note": policy_note,
                        },
                        "outbound_transportation": {
                            "type": trans.get("type", ""),
                            "departure_station": trans.get("departure_station", ""),
                            "arrival_station": trans.get("arrival_station", ""),
                            "departure_time": schedule.get("departure", ""),
                            "arrival_time": schedule.get("arrival", ""),
                            "price": trans_price,
                            "train_name": trans.get("train_name", ""),
                        },
                        "return_transportation": {
                            "type": trans.get("type", ""),
                            "departure_station": trans.get("arrival_station", ""),
                            "arrival_station": trans.get("departure_station", ""),
                            "departure_time": "18:00",
                            "arrival_time": "",
                            "price": trans_price,
                            "train_name": trans.get("train_name", ""),
                        },
                        "hotel": {
                            "name": hotel.get("name", ""),
                            "area": hotel.get("area", ""),
                            "price_per_night": hotel.get("price_per_night", 0),
                            "nights": nights,
                            "total_price": hotel_price,
                            "rating": hotel.get("rating"),
                        },
                    }
                )
                plan_count += 1
            if plan_count >= 3:
                break

    if params.budget:
        plans.sort(
            key=lambda p: (
                0 if p["summary"]["policy_status"] == "OK" else 1,
                p["summary"]["estimated_total"],
            )
        )

    return {"success": True, "plans": plans, "total_plans": len(plans)}


def plan_generator_declaration() -> FunctionDeclaration:
    return FunctionDeclaration(
        name="plan_generator",
        description="出発地・目的地・日程から出張プランを複数生成します（内部で交通/ホテル検索を行う）。日帰りはreturn_date省略可。",
        parameters={
            "type": "object",
            "properties": {
                "departure_location": {"type": "string", "description": "出発地（例: 東京）"},
                "destination": {"type": "string", "description": "目的地（例: 大阪）"},
                "depart_date": {"type": "string", "description": "出発日（YYYY-MM-DD）"},
                "return_date": {"type": "string", "description": "帰着日（YYYY-MM-DD、日帰りなら省略可）"},
                "budget": {"type": "integer", "description": "予算上限（円）"},
                "preferred_transportation": {"type": "string", "description": "希望交通手段（新幹線、飛行機など）"},
            },
            "required": ["departure_location", "destination", "depart_date"],
        },
    )

