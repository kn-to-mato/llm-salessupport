"""宿泊先検索ツール（モック）"""
from typing import Any, Dict, List, Optional
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from ddtrace.llmobs.decorators import tool as llmobs_tool


# モックホテルデータ
HOTEL_DATA = {
    "大阪": [
        {
            "name": "ダイワロイネットホテル大阪北浜",
            "area": "北浜",
            "price_per_night": 9800,
            "rating": 4.2,
            "amenities": ["朝食付きプランあり", "Wi-Fi", "コインランドリー"],
            "distance_to_station": "北浜駅徒歩3分"
        },
        {
            "name": "東横イン新大阪中央口本館",
            "area": "新大阪",
            "price_per_night": 7500,
            "rating": 3.8,
            "amenities": ["朝食無料", "Wi-Fi"],
            "distance_to_station": "新大阪駅徒歩5分"
        },
        {
            "name": "アパホテル大阪梅田",
            "area": "梅田",
            "price_per_night": 8200,
            "rating": 3.9,
            "amenities": ["大浴場", "Wi-Fi"],
            "distance_to_station": "梅田駅徒歩7分"
        },
        {
            "name": "ドーミーイン心斎橋",
            "area": "心斎橋",
            "price_per_night": 11000,
            "rating": 4.4,
            "amenities": ["天然温泉", "夜鳴きそば", "朝食付き", "Wi-Fi"],
            "distance_to_station": "心斎橋駅徒歩5分"
        },
        {
            "name": "コンフォートホテル大阪心斎橋",
            "area": "心斎橋",
            "price_per_night": 8500,
            "rating": 4.0,
            "amenities": ["朝食無料", "Wi-Fi", "加湿空気清浄機"],
            "distance_to_station": "心斎橋駅徒歩3分"
        }
    ],
    "福岡": [
        {
            "name": "ダイワロイネットホテル博多祇園",
            "area": "祇園",
            "price_per_night": 9500,
            "rating": 4.3,
            "amenities": ["朝食付きプランあり", "Wi-Fi"],
            "distance_to_station": "祇園駅徒歩2分"
        },
        {
            "name": "東横イン博多駅前祇園",
            "area": "祇園",
            "price_per_night": 7000,
            "rating": 3.7,
            "amenities": ["朝食無料", "Wi-Fi"],
            "distance_to_station": "祇園駅徒歩5分"
        },
        {
            "name": "ドーミーインPREMIUM博多・キャナルシティ前",
            "area": "キャナルシティ",
            "price_per_night": 12000,
            "rating": 4.5,
            "amenities": ["天然温泉", "夜鳴きそば", "朝食付き", "Wi-Fi"],
            "distance_to_station": "中洲川端駅徒歩7分"
        }
    ],
    "名古屋": [
        {
            "name": "ダイワロイネットホテル名古屋駅前",
            "area": "名古屋駅",
            "price_per_night": 10000,
            "rating": 4.2,
            "amenities": ["朝食付きプランあり", "Wi-Fi"],
            "distance_to_station": "名古屋駅徒歩5分"
        },
        {
            "name": "東横イン名古屋駅新幹線口",
            "area": "名古屋駅",
            "price_per_night": 7200,
            "rating": 3.8,
            "amenities": ["朝食無料", "Wi-Fi"],
            "distance_to_station": "名古屋駅徒歩3分"
        },
        {
            "name": "アパホテル名古屋栄",
            "area": "栄",
            "price_per_night": 7800,
            "rating": 3.7,
            "amenities": ["大浴場", "Wi-Fi"],
            "distance_to_station": "栄駅徒歩5分"
        }
    ],
    "仙台": [
        {
            "name": "ダイワロイネットホテル仙台",
            "area": "仙台駅",
            "price_per_night": 9000,
            "rating": 4.1,
            "amenities": ["朝食付きプランあり", "Wi-Fi"],
            "distance_to_station": "仙台駅徒歩5分"
        },
        {
            "name": "東横イン仙台駅西口中央",
            "area": "仙台駅",
            "price_per_night": 6800,
            "rating": 3.8,
            "amenities": ["朝食無料", "Wi-Fi"],
            "distance_to_station": "仙台駅徒歩3分"
        },
        {
            "name": "ドーミーイン仙台駅前",
            "area": "仙台駅",
            "price_per_night": 10500,
            "rating": 4.4,
            "amenities": ["天然温泉", "夜鳴きそば", "朝食付き", "Wi-Fi"],
            "distance_to_station": "仙台駅徒歩7分"
        }
    ],
    "札幌": [
        {
            "name": "ダイワロイネットホテル札幌すすきの",
            "area": "すすきの",
            "price_per_night": 9500,
            "rating": 4.2,
            "amenities": ["朝食付きプランあり", "Wi-Fi"],
            "distance_to_station": "すすきの駅徒歩3分"
        },
        {
            "name": "東横イン札幌駅北口",
            "area": "札幌駅",
            "price_per_night": 7000,
            "rating": 3.8,
            "amenities": ["朝食無料", "Wi-Fi"],
            "distance_to_station": "札幌駅徒歩5分"
        },
        {
            "name": "ドーミーインPREMIUM札幌",
            "area": "狸小路",
            "price_per_night": 11500,
            "rating": 4.5,
            "amenities": ["天然温泉", "夜鳴きそば", "朝食付き", "Wi-Fi"],
            "distance_to_station": "大通駅徒歩5分"
        }
    ]
}


class HotelSearchInput(BaseModel):
    """ホテル検索入力"""
    destination: str = Field(..., description="目的地（例：大阪）")
    nights: int = Field(1, description="宿泊数")
    max_price_per_night: Optional[int] = Field(None, description="1泊あたりの上限金額")
    preferred_area: Optional[str] = Field(None, description="希望エリア")


class HotelSearchTool(BaseTool):
    """宿泊先を検索するツール"""
    
    name: str = "hotel_search"
    description: str = """目的地で利用可能なホテルを検索します。
    料金、エリア、設備などの情報を取得できます。"""
    args_schema: type[BaseModel] = HotelSearchInput
    
    @llmobs_tool(name="hotel_search")
    def _run(
        self,
        destination: str,
        nights: int = 1,
        max_price_per_night: Optional[int] = None,
        preferred_area: Optional[str] = None,
    ) -> Dict[str, Any]:
        """ホテルを検索"""
        # 目的地を正規化
        dest = self._normalize_location(destination)
        
        hotels = HOTEL_DATA.get(dest, [])
        
        if not hotels:
            return {
                "found": False,
                "message": f"{destination}のホテル情報が見つかりませんでした。",
                "hotels": []
            }
        
        # フィルタリング
        filtered = hotels
        if max_price_per_night:
            filtered = [h for h in filtered if h["price_per_night"] <= max_price_per_night]
        if preferred_area:
            area_filtered = [h for h in filtered if preferred_area in h["area"]]
            if area_filtered:
                filtered = area_filtered
        
        # 総額を計算
        result_hotels = []
        for hotel in filtered:
            hotel_info = hotel.copy()
            hotel_info["nights"] = nights
            hotel_info["total_price"] = hotel["price_per_night"] * nights
            result_hotels.append(hotel_info)
        
        # 評価順にソート
        result_hotels.sort(key=lambda x: x["rating"], reverse=True)
        
        return {
            "found": True,
            "destination": destination,
            "nights": nights,
            "hotels": result_hotels,
            "total_options": len(result_hotels)
        }
    
    def _normalize_location(self, location: str) -> str:
        """地名を正規化"""
        mappings = {
            "大阪": "大阪",
            "osaka": "大阪",
            "新大阪": "大阪",
            "福岡": "福岡",
            "博多": "福岡",
            "名古屋": "名古屋",
            "nagoya": "名古屋",
            "仙台": "仙台",
            "sendai": "仙台",
            "札幌": "札幌",
            "sapporo": "札幌",
        }
        return mappings.get(location.lower().strip(), location)
    
    async def _arun(self, **kwargs) -> Dict[str, Any]:
        """非同期実行"""
        return self._run(**kwargs)

