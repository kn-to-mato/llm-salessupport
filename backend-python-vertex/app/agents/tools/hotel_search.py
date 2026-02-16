"""Hotel search tool (mock)."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field
from vertexai.generative_models import FunctionDeclaration


class HotelSearchInput(BaseModel):
    destination: str = Field(..., description="宿泊地（例: 大阪）")
    nights: int = Field(1, description="宿泊数")
    max_price_per_night: Optional[int] = Field(None, description="1泊あたりの上限（円）")
    preferred_area: Optional[str] = Field(None, description="希望エリア")


MOCK_HOTELS = {
    "大阪": [
        {"name": "ドーミーイン心斎橋", "area": "心斎橋", "price_per_night": 12000, "rating": 4.2},
        {"name": "ダイワロイネットホテル大阪北浜", "area": "北浜", "price_per_night": 10800, "rating": 4.0},
        {"name": "コンフォートホテル新大阪", "area": "新大阪", "price_per_night": 8500, "rating": 3.8},
    ],
    "名古屋": [
        {"name": "ダイワロイネットホテル名古屋", "area": "名駅", "price_per_night": 9500, "rating": 4.1},
    ],
    "福岡": [
        {"name": "ドーミーイン博多", "area": "博多", "price_per_night": 11000, "rating": 4.3},
    ],
}


def run_hotel_search(**kwargs) -> Dict[str, Any]:
    params = HotelSearchInput(**kwargs)
    hotels = MOCK_HOTELS.get(params.destination, [])

    if params.preferred_area:
        hotels = [h for h in hotels if h.get("area") == params.preferred_area] or hotels

    if params.max_price_per_night is not None:
        hotels = [h for h in hotels if h.get("price_per_night", 0) <= params.max_price_per_night] or hotels

    # decorate with nights/total_price for compatibility with plan_generator usage
    hydrated = []
    for h in hotels:
        hydrated.append(
            {
                **h,
                "nights": params.nights,
                "total_price": h.get("price_per_night", 0) * params.nights,
            }
        )

    return {
        "found": bool(hydrated),
        "destination": params.destination,
        "nights": params.nights,
        "hotels": hydrated,
        "total_hotels": len(hydrated),
    }


def hotel_search_declaration() -> FunctionDeclaration:
    return FunctionDeclaration(
        name="hotel_search",
        description="目的地周辺のホテル候補を検索します（モック）。",
        parameters={
            "type": "object",
            "properties": {
                "destination": {"type": "string", "description": "宿泊地（例: 大阪）"},
                "nights": {"type": "integer", "description": "宿泊数（デフォルト1）"},
                "max_price_per_night": {"type": "integer", "description": "1泊あたりの上限（円）"},
                "preferred_area": {"type": "string", "description": "希望エリア"},
            },
            "required": ["destination"],
        },
    )

