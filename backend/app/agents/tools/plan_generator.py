"""出張プラン生成ツール"""
from typing import Any, Dict, List, Optional
import uuid
from langchain.tools import BaseTool
from pydantic import BaseModel, Field


class PlanGeneratorInput(BaseModel):
    """プラン生成入力"""
    departure_location: str = Field(..., description="出発地")
    destination: str = Field(..., description="目的地")
    depart_date: str = Field(..., description="出発日（YYYY-MM-DD）")
    return_date: str = Field(..., description="帰着日（YYYY-MM-DD）")
    transportation_options: List[Dict] = Field(..., description="交通手段の候補リスト")
    hotel_options: List[Dict] = Field(..., description="ホテルの候補リスト")
    budget: Optional[int] = Field(None, description="予算上限")
    policy_check_results: Optional[Dict] = Field(None, description="規程チェック結果")


class PlanGeneratorTool(BaseTool):
    """出張プランを生成するツール"""
    
    name: str = "plan_generator"
    description: str = """交通手段とホテルの候補から、最適な出張プランを複数パターン生成します。
    予算や規程を考慮して、おすすめ順に並べて返します。"""
    args_schema: type[BaseModel] = PlanGeneratorInput
    
    def _run(
        self,
        departure_location: str,
        destination: str,
        depart_date: str,
        return_date: str,
        transportation_options: List[Dict],
        hotel_options: List[Dict],
        budget: Optional[int] = None,
        policy_check_results: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """プランを生成"""
        plans = []
        
        # 宿泊数を計算
        from datetime import datetime
        try:
            dep_date = datetime.strptime(depart_date, "%Y-%m-%d")
            ret_date = datetime.strptime(return_date, "%Y-%m-%d")
            nights = (ret_date - dep_date).days
        except:
            nights = 1
        
        # 交通手段ごとにプランを生成
        plan_labels = ["A", "B", "C", "D", "E"]
        plan_count = 0
        
        for trans in transportation_options[:3]:  # 上位3つの交通手段
            for hotel in hotel_options[:2]:  # 上位2つのホテル
                if plan_count >= 3:
                    break
                
                # スケジュールから最初の便を取得
                schedule = trans.get("schedules", [{}])[0] if trans.get("schedules") else {}
                
                # 片道料金
                trans_price = schedule.get("price", trans.get("price", 0))
                round_trip_trans = trans_price * 2
                
                # 宿泊料金
                hotel_price = hotel.get("price_per_night", 0) * nights
                
                # 合計
                total = round_trip_trans + hotel_price
                
                # 予算チェック
                policy_status = "OK"
                policy_note = None
                
                if budget and total > budget:
                    policy_status = "注意"
                    policy_note = f"予算 {budget:,}円を{total - budget:,}円超過しています"
                
                # 1泊15000円超過チェック
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
                        "departure_time": "18:00",  # 仮の復路時刻
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
