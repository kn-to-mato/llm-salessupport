"""出張プラン生成ツール"""
from typing import Any, Dict, List, Optional
import uuid
from langchain.tools import BaseTool
from pydantic import BaseModel, Field


class PlanGeneratorInput(BaseModel):
    """プラン生成入力"""
    departure_location: str = Field(..., description="出発地（例: 東京）")
    destination: str = Field(..., description="目的地（例: 大阪）")
    depart_date: str = Field(..., description="出発日（YYYY-MM-DD形式、例: 2024-12-09）")
    return_date: Optional[str] = Field(None, description="帰着日（YYYY-MM-DD形式、日帰りの場合は省略可）")
    budget: Optional[int] = Field(None, description="予算上限（円）")
    preferred_transportation: Optional[str] = Field(None, description="希望交通手段（新幹線、飛行機など）")


class PlanGeneratorTool(BaseTool):
    """出張プランを生成するツール"""
    
    name: str = "plan_generator"
    description: str = """出発地・目的地・日程から最適な出張プランを複数パターン生成します。
    内部で交通手段とホテルを検索し、予算や規程を考慮したプランを提案します。
    日帰りの場合はreturn_dateを省略できます。"""
    args_schema: type[BaseModel] = PlanGeneratorInput
    
    def _run(
        self,
        departure_location: str,
        destination: str,
        depart_date: str,
        return_date: Optional[str] = None,
        budget: Optional[int] = None,
        preferred_transportation: Optional[str] = None,
    ) -> Dict[str, Any]:
        """プランを生成（内部で交通・ホテル検索を実行）"""
        from .transportation_search import TransportationSearchTool
        from .hotel_search import HotelSearchTool
        
        plans = []
        
        # 交通手段を検索
        trans_tool = TransportationSearchTool()
        trans_result = trans_tool._run(
            departure=departure_location,
            destination=destination,
            preferred_type=preferred_transportation,
        )
        transportation_options = trans_result.get("options", [])
        
        # 宿泊数を計算
        from datetime import datetime
        is_day_trip = return_date is None
        nights = 0
        
        if not is_day_trip:
            try:
                dep_date = datetime.strptime(depart_date, "%Y-%m-%d")
                ret_date = datetime.strptime(return_date, "%Y-%m-%d")
                nights = (ret_date - dep_date).days
            except:
                nights = 1
        
        # ホテルを検索（日帰りでない場合）
        hotel_options = []
        if not is_day_trip and nights > 0:
            hotel_tool = HotelSearchTool()
            hotel_result = hotel_tool._run(
                destination=destination,
                nights=nights,
                max_price_per_night=15000,
            )
            hotel_options = hotel_result.get("hotels", [])
        
        # 交通手段ごとにプランを生成
        plan_labels = ["A", "B", "C", "D", "E"]
        plan_count = 0
        
        if is_day_trip:
            # 日帰りプラン（ホテルなし）
            for trans in transportation_options[:3]:
                if plan_count >= 3:
                    break
                
                schedule = trans.get("schedules", [{}])[0] if trans.get("schedules") else {}
                trans_price = schedule.get("price", trans.get("price", 0))
                round_trip_trans = trans_price * 2
                total = round_trip_trans
                
                policy_status = "OK"
                policy_note = None
                if budget and total > budget:
                    policy_status = "注意"
                    policy_note = f"予算 {budget:,}円を{total - budget:,}円超過しています"
                
                plan = {
                    "plan_id": str(uuid.uuid4()),
                    "label": f"プラン{plan_labels[plan_count]}",
                    "summary": {
                        "depart_date": depart_date,
                        "return_date": depart_date,  # 日帰りなので同日
                        "destination": destination,
                        "transportation": f"{trans.get('type', '交通手段')}（{trans.get('train_name', '')}）",
                        "hotel": "なし（日帰り）",
                        "estimated_total": total,
                        "policy_status": policy_status,
                        "policy_note": policy_note
                    },
                    "outbound_transportation": {
                        "type": trans.get("type", ""),
                        "departure_station": trans.get("departure_station", ""),
                        "arrival_station": trans.get("arrival_station", ""),
                        "departure_time": schedule.get("departure", ""),
                        "arrival_time": schedule.get("arrival", ""),
                        "price": trans_price,
                        "train_name": trans.get("train_name", "")
                    },
                    "return_transportation": {
                        "type": trans.get("type", ""),
                        "departure_station": trans.get("arrival_station", ""),
                        "arrival_station": trans.get("departure_station", ""),
                        "departure_time": "18:00",
                        "arrival_time": "",
                        "price": trans_price,
                        "train_name": trans.get("train_name", "")
                    },
                    "hotel": None
                }
                plans.append(plan)
                plan_count += 1
        else:
            # 宿泊ありプラン
            for trans in transportation_options[:3]:
                for hotel in hotel_options[:2]:
                    if plan_count >= 3:
                        break
                    
                    schedule = trans.get("schedules", [{}])[0] if trans.get("schedules") else {}
                    trans_price = schedule.get("price", trans.get("price", 0))
                    round_trip_trans = trans_price * 2
                    hotel_price = hotel.get("price_per_night", 0) * nights
                    total = round_trip_trans + hotel_price
                    
                    policy_status = "OK"
                    policy_note = None
                    
                    if budget and total > budget:
                        policy_status = "注意"
                        policy_note = f"予算 {budget:,}円を{total - budget:,}円超過しています"
                    
                    if hotel.get("price_per_night", 0) > 15000:
                        policy_status = "NG"
                        policy_note = "宿泊費が規程上限（15,000円/泊）を超過しています"
                    
                    plan = {
                        "plan_id": str(uuid.uuid4()),
                        "label": f"プラン{plan_labels[plan_count]}",
                        "summary": {
                            "depart_date": depart_date,
                            "return_date": return_date,
                            "destination": destination,
                            "transportation": f"{trans.get('type', '交通手段')}（{trans.get('train_name', '')}）",
                            "hotel": f"{hotel.get('name', 'ホテル')} {nights}泊",
                            "estimated_total": total,
                            "policy_status": policy_status,
                            "policy_note": policy_note
                        },
                        "outbound_transportation": {
                            "type": trans.get("type", ""),
                            "departure_station": trans.get("departure_station", ""),
                            "arrival_station": trans.get("arrival_station", ""),
                            "departure_time": schedule.get("departure", ""),
                            "arrival_time": schedule.get("arrival", ""),
                            "price": trans_price,
                            "train_name": trans.get("train_name", "")
                        },
                        "return_transportation": {
                            "type": trans.get("type", ""),
                            "departure_station": trans.get("arrival_station", ""),
                            "arrival_station": trans.get("departure_station", ""),
                            "departure_time": "18:00",
                            "arrival_time": "",
                            "price": trans_price,
                            "train_name": trans.get("train_name", "")
                        },
                        "hotel": {
                            "name": hotel.get("name", ""),
                            "area": hotel.get("area", ""),
                            "price_per_night": hotel.get("price_per_night", 0),
                            "nights": nights,
                            "total_price": hotel_price,
                            "rating": hotel.get("rating")
                        }
                    }
                    plans.append(plan)
                    plan_count += 1
                
                if plan_count >= 3:
                    break
        
        # 予算内のプランを優先してソート
        if budget:
            plans.sort(key=lambda p: (
                0 if p["summary"]["policy_status"] == "OK" else 1,
                p["summary"]["estimated_total"]
            ))
        
        return {
            "success": True,
            "plans": plans,
            "total_plans": len(plans)
        }
    
    async def _arun(self, **kwargs) -> Dict[str, Any]:
        """非同期実行"""
        return self._run(**kwargs)
