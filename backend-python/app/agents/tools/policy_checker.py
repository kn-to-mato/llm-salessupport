"""社内旅費規程チェックツール（モック）"""
from typing import Any, Dict, Optional
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from ddtrace.llmobs.decorators import tool as llmobs_tool


# モック社内旅費規程
TRAVEL_POLICY = {
    "daily_budget": {
        "domestic": {
            "transportation": 50000,  # 1日あたりの交通費上限
            "accommodation": 15000,   # 1泊あたりの宿泊費上限
            "meals": 3000,            # 1日あたりの食事代
        },
        "international": {
            "transportation": 200000,
            "accommodation": 30000,
            "meals": 5000,
        }
    },
    "transportation_rules": {
        "新幹線": {
            "allowed": True,
            "class": "普通車指定席",
            "note": "グリーン車は部長以上のみ利用可"
        },
        "飛行機": {
            "allowed": True,
            "class": "エコノミークラス",
            "note": "国内線はエコノミーのみ。300km以上の移動で利用可"
        },
        "高速バス": {
            "allowed": True,
            "class": "指定なし",
            "note": "夜行バスは原則禁止"
        }
    },
    "accommodation_rules": {
        "max_stars": 4,
        "preferred_chains": ["東横イン", "アパホテル", "ドーミーイン", "コンフォートホテル", "ダイワロイネット"],
        "note": "ビジネスホテルを優先すること"
    },
    "approval_rules": {
        "same_day": "事前申請不要、事後報告",
        "overnight": "3営業日前までに申請",
        "over_budget": "部長承認が必要"
    }
}


class PolicyCheckInput(BaseModel):
    """規程チェック入力"""
    transportation_type: Optional[str] = Field(None, description="交通手段タイプ（新幹線、飛行機等）")
    transportation_cost: Optional[int] = Field(None, description="交通費総額")
    hotel_cost_per_night: Optional[int] = Field(None, description="1泊あたりの宿泊費")
    total_nights: Optional[int] = Field(None, description="宿泊数")
    total_budget: Optional[int] = Field(None, description="総予算")
    is_domestic: bool = Field(True, description="国内出張かどうか")


class PolicyCheckerTool(BaseTool):
    """社内旅費規程をチェックするツール"""
    
    name: str = "policy_checker"
    description: str = """社内旅費規程に照らして、出張プランが規程に適合しているかチェックします。
    交通手段、交通費、宿泊費などを入力すると、OK/NG/注意の判定と詳細を返します。"""
    args_schema: type[BaseModel] = PolicyCheckInput
    
    @llmobs_tool(name="policy_checker")
    def _run(
        self,
        transportation_type: Optional[str] = None,
        transportation_cost: Optional[int] = None,
        hotel_cost_per_night: Optional[int] = None,
        total_nights: Optional[int] = None,
        total_budget: Optional[int] = None,
        is_domestic: bool = True,
    ) -> Dict[str, Any]:
        """規程チェックを実行"""
        results = {
            "status": "OK",
            "checks": [],
            "warnings": [],
            "errors": []
        }
        
        region = "domestic" if is_domestic else "international"
        budget_limits = TRAVEL_POLICY["daily_budget"][region]
        
        # 交通手段チェック
        if transportation_type:
            trans_rule = TRAVEL_POLICY["transportation_rules"].get(transportation_type)
            if trans_rule:
                if trans_rule["allowed"]:
                    results["checks"].append({
                        "item": "交通手段",
                        "status": "OK",
                        "detail": f"{transportation_type}は利用可。{trans_rule['note']}"
                    })
                else:
                    results["errors"].append(f"{transportation_type}は規程上利用不可です。")
                    results["status"] = "NG"
            else:
                results["warnings"].append(f"{transportation_type}は規程に明記されていません。要確認。")
                if results["status"] == "OK":
                    results["status"] = "注意"
        
        # 交通費チェック
        if transportation_cost is not None:
            limit = budget_limits["transportation"]
            if transportation_cost <= limit:
                results["checks"].append({
                    "item": "交通費",
                    "status": "OK",
                    "detail": f"交通費 {transportation_cost:,}円は上限 {limit:,}円以内です。"
                })
            else:
                results["warnings"].append(
                    f"交通費 {transportation_cost:,}円が上限 {limit:,}円を超えています。部長承認が必要です。"
                )
                if results["status"] == "OK":
                    results["status"] = "注意"
        
        # 宿泊費チェック
        if hotel_cost_per_night is not None:
            limit = budget_limits["accommodation"]
            if hotel_cost_per_night <= limit:
                results["checks"].append({
                    "item": "宿泊費",
                    "status": "OK",
                    "detail": f"1泊 {hotel_cost_per_night:,}円は上限 {limit:,}円以内です。"
                })
            else:
                results["errors"].append(
                    f"1泊 {hotel_cost_per_night:,}円が上限 {limit:,}円を超えています。"
                )
                results["status"] = "NG"
        
        # 総予算サマリー
        if total_budget is not None:
            results["summary"] = {
                "total_budget": total_budget,
                "policy_check": results["status"],
                "approval_required": results["status"] != "OK"
            }
        
        return results
    
    async def _arun(self, **kwargs) -> Dict[str, Any]:
        """非同期実行"""
        return self._run(**kwargs)

