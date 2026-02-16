"""Transportation search tool (mock)."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field
from vertexai.generative_models import FunctionDeclaration


class TransportationSearchInput(BaseModel):
    departure: str = Field(..., description="出発地（例: 東京）")
    destination: str = Field(..., description="目的地（例: 大阪）")
    preferred_type: Optional[str] = Field(None, description="希望交通手段（新幹線、飛行機等）")
    max_price: Optional[int] = Field(None, description="片道上限金額（円）")


MOCK_ROUTES = {
    ("東京", "大阪"): [
        {
            "type": "新幹線",
            "train_name": "のぞみ",
            "departure_station": "東京駅",
            "arrival_station": "新大阪駅",
            "schedules": [
                {"departure": "06:00", "arrival": "08:22", "price": 14720},
                {"departure": "08:00", "arrival": "10:22", "price": 14720},
            ],
            "duration_minutes": 142,
        },
        {
            "type": "新幹線",
            "train_name": "ひかり",
            "departure_station": "東京駅",
            "arrival_station": "新大阪駅",
            "schedules": [
                {"departure": "06:33", "arrival": "09:23", "price": 14400},
            ],
            "duration_minutes": 170,
        },
        {
            "type": "飛行機",
            "train_name": "ANA/JAL",
            "departure_station": "羽田空港",
            "arrival_station": "伊丹空港",
            "schedules": [
                {"departure": "07:00", "arrival": "08:10", "price": 22000},
            ],
            "duration_minutes": 70,
        },
    ],
    ("東京", "名古屋"): [
        {
            "type": "新幹線",
            "train_name": "のぞみ",
            "departure_station": "東京駅",
            "arrival_station": "名古屋駅",
            "schedules": [{"departure": "08:00", "arrival": "09:40", "price": 11300}],
            "duration_minutes": 100,
        }
    ],
    ("東京", "福岡"): [
        {
            "type": "飛行機",
            "train_name": "ANA/JAL",
            "departure_station": "羽田空港",
            "arrival_station": "福岡空港",
            "schedules": [{"departure": "09:00", "arrival": "11:05", "price": 32000}],
            "duration_minutes": 125,
        }
    ],
}


def run_transportation_search(**kwargs) -> Dict[str, Any]:
    params = TransportationSearchInput(**kwargs)
    key = (params.departure, params.destination)
    options = MOCK_ROUTES.get(key, [])

    # preferred filter
    if params.preferred_type:
        options = [o for o in options if o.get("type") == params.preferred_type] or options

    # max_price filter (uses first schedule price)
    if params.max_price is not None:
        filtered = []
        for o in options:
            schedules = o.get("schedules") or []
            price = (schedules[0].get("price") if schedules else None) or 0
            if price <= params.max_price:
                filtered.append(o)
        options = filtered or options

    return {
        "found": bool(options),
        "departure": params.departure,
        "destination": params.destination,
        "options": options,
        "total_options": len(options),
    }


def transportation_search_declaration() -> FunctionDeclaration:
    return FunctionDeclaration(
        name="transportation_search",
        description="出発地・目的地間の交通手段（新幹線・飛行機等）を検索します（モック）。",
        parameters={
            "type": "object",
            "properties": {
                "departure": {"type": "string", "description": "出発地（例: 東京）"},
                "destination": {"type": "string", "description": "目的地（例: 大阪）"},
                "preferred_type": {"type": "string", "description": "希望交通手段（新幹線、飛行機等）"},
                "max_price": {"type": "integer", "description": "片道上限金額（円）"},
            },
            "required": ["departure", "destination"],
        },
    )

