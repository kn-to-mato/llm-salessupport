"""交通手段検索ツール（モック）"""
from typing import Any, Dict, List, Optional
from langchain.tools import BaseTool
from pydantic import BaseModel, Field


# モック交通データ
TRANSPORTATION_DATA = {
    ("東京", "大阪"): [
        {
            "type": "新幹線",
            "train_name": "のぞみ",
            "departure_station": "東京駅",
            "arrival_station": "新大阪駅",
            "schedules": [
                {"departure": "06:00", "arrival": "08:22", "price": 14720},
                {"departure": "08:00", "arrival": "10:22", "price": 14720},
                {"departure": "09:00", "arrival": "11:22", "price": 14720},
                {"departure": "10:00", "arrival": "12:22", "price": 14720},
                {"departure": "12:00", "arrival": "14:22", "price": 14720},
            ],
            "duration_minutes": 142
        },
        {
            "type": "新幹線",
            "train_name": "ひかり",
            "departure_station": "東京駅",
            "arrival_station": "新大阪駅",
            "schedules": [
                {"departure": "06:33", "arrival": "09:23", "price": 14400},
                {"departure": "09:33", "arrival": "12:23", "price": 14400},
            ],
            "duration_minutes": 170
        },
        {
            "type": "飛行機",
            "train_name": "JAL/ANA",
            "departure_station": "羽田空港",
            "arrival_station": "伊丹空港",
            "schedules": [
                {"departure": "07:00", "arrival": "08:10", "price": 25000},
                {"departure": "09:00", "arrival": "10:10", "price": 22000},
                {"departure": "12:00", "arrival": "13:10", "price": 18000},
            ],
            "duration_minutes": 70,
            "note": "空港までの移動時間を考慮すると新幹線と同程度"
        }
    ],
    ("東京", "福岡"): [
        {
            "type": "飛行機",
            "train_name": "JAL/ANA",
            "departure_station": "羽田空港",
            "arrival_station": "福岡空港",
            "schedules": [
                {"departure": "07:15", "arrival": "09:20", "price": 35000},
                {"departure": "09:00", "arrival": "11:05", "price": 32000},
                {"departure": "12:00", "arrival": "14:05", "price": 28000},
                {"departure": "18:00", "arrival": "20:05", "price": 30000},
            ],
            "duration_minutes": 125
        },
        {
            "type": "新幹線",
            "train_name": "のぞみ",
            "departure_station": "東京駅",
            "arrival_station": "博多駅",
            "schedules": [
                {"departure": "06:00", "arrival": "10:53", "price": 23810},
                {"departure": "08:00", "arrival": "12:53", "price": 23810},
            ],
            "duration_minutes": 293,
            "note": "所要時間が長いため飛行機推奨"
        }
    ],
    ("東京", "名古屋"): [
        {
            "type": "新幹線",
            "train_name": "のぞみ",
            "departure_station": "東京駅",
            "arrival_station": "名古屋駅",
            "schedules": [
                {"departure": "06:00", "arrival": "07:40", "price": 11300},
                {"departure": "08:00", "arrival": "09:40", "price": 11300},
                {"departure": "09:00", "arrival": "10:40", "price": 11300},
                {"departure": "10:00", "arrival": "11:40", "price": 11300},
            ],
            "duration_minutes": 100
        },
        {
            "type": "新幹線",
            "train_name": "ひかり",
            "departure_station": "東京駅",
            "arrival_station": "名古屋駅",
            "schedules": [
                {"departure": "06:33", "arrival": "08:33", "price": 11090},
                {"departure": "09:33", "arrival": "11:33", "price": 11090},
            ],
            "duration_minutes": 120
        }
    ],
    ("東京", "仙台"): [
        {
            "type": "新幹線",
            "train_name": "はやぶさ",
            "departure_station": "東京駅",
            "arrival_station": "仙台駅",
            "schedules": [
                {"departure": "06:32", "arrival": "08:04", "price": 11410},
                {"departure": "08:20", "arrival": "09:52", "price": 11410},
                {"departure": "09:36", "arrival": "11:08", "price": 11410},
            ],
            "duration_minutes": 92
        }
    ],
    ("東京", "札幌"): [
        {
            "type": "飛行機",
            "train_name": "JAL/ANA",
            "departure_station": "羽田空港",
            "arrival_station": "新千歳空港",
            "schedules": [
                {"departure": "07:00", "arrival": "08:35", "price": 38000},
                {"departure": "09:00", "arrival": "10:35", "price": 35000},
                {"departure": "12:00", "arrival": "13:35", "price": 30000},
            ],
            "duration_minutes": 95
        }
    ]
}


class TransportationSearchInput(BaseModel):
    """交通手段検索入力"""
    departure: str = Field(..., description="出発地（例：東京）")
    destination: str = Field(..., description="目的地（例：大阪）")
    preferred_type: Optional[str] = Field(None, description="希望交通手段（新幹線、飛行機等）")
    max_price: Optional[int] = Field(None, description="片道上限金額")


class TransportationSearchTool(BaseTool):
    """交通手段を検索するツール"""
    
    name: str = "transportation_search"
    description: str = """出発地と目的地から利用可能な交通手段を検索します。
    新幹線や飛行機の時刻表、料金などを取得できます。"""
    args_schema: type[BaseModel] = TransportationSearchInput
    
    def _run(
        self,
        departure: str,
        destination: str,
        preferred_type: Optional[str] = None,
        max_price: Optional[int] = None,
    ) -> Dict[str, Any]:
        """交通手段を検索"""
        # 出発地と目的地を正規化
        dep = self._normalize_location(departure)
        dest = self._normalize_location(destination)
        
        # データ検索
        key = (dep, dest)
        reverse_key = (dest, dep)
        
        results = TRANSPORTATION_DATA.get(key, [])
        if not results:
            results = TRANSPORTATION_DATA.get(reverse_key, [])
            if results:
                # 往路と復路を入れ替え
                results = self._swap_direction(results)
        
        if not results:
            return {
                "found": False,
                "message": f"{departure}から{destination}への交通手段が見つかりませんでした。",
                "options": []
            }
        
        # フィルタリング
        filtered = results
        if preferred_type:
            filtered = [r for r in filtered if r["type"] == preferred_type]
        if max_price:
            filtered = [r for r in filtered if any(s["price"] <= max_price for s in r["schedules"])]
        
        return {
            "found": True,
            "departure": departure,
            "destination": destination,
            "options": filtered,
            "total_options": len(filtered)
        }
    
    def _normalize_location(self, location: str) -> str:
        """地名を正規化"""
        mappings = {
            "東京": "東京",
            "tokyo": "東京",
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
    
    def _swap_direction(self, results: List[Dict]) -> List[Dict]:
        """往路と復路を入れ替え"""
        swapped = []
        for r in results:
            new_r = r.copy()
            new_r["departure_station"], new_r["arrival_station"] = r["arrival_station"], r["departure_station"]
            swapped.append(new_r)
        return swapped
    
    async def _arun(self, **kwargs) -> Dict[str, Any]:
        """非同期実行"""
        return self._run(**kwargs)
