"""Travel policy checker tool (mock)."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field
from vertexai.generative_models import FunctionDeclaration


TRAVEL_POLICY = {
    "daily_budget": {
        "domestic": {"transportation": 50000, "accommodation": 15000, "meals": 3000},
        "international": {"transportation": 200000, "accommodation": 30000, "meals": 5000},
    },
    "transportation_rules": {
        "新幹線": {"allowed": True, "class": "普通車指定席", "note": "グリーン車は部長以上のみ利用可"},
        "飛行機": {"allowed": True, "class": "エコノミークラス", "note": "国内線はエコノミーのみ。300km以上の移動で利用可"},
        "高速バス": {"allowed": True, "class": "指定なし", "note": "夜行バスは原則禁止"},
    },
}


class PolicyCheckInput(BaseModel):
    transportation_type: Optional[str] = Field(None, description="交通手段タイプ（新幹線、飛行機等）")
    transportation_cost: Optional[int] = Field(None, description="交通費総額")
    hotel_cost_per_night: Optional[int] = Field(None, description="1泊あたりの宿泊費")
    total_nights: Optional[int] = Field(None, description="宿泊数")
    total_budget: Optional[int] = Field(None, description="総予算")
    is_domestic: bool = Field(True, description="国内出張かどうか")


def run_policy_checker(**kwargs) -> Dict[str, Any]:
    params = PolicyCheckInput(**kwargs)
    results: Dict[str, Any] = {"status": "OK", "checks": [], "warnings": [], "errors": []}

    region = "domestic" if params.is_domestic else "international"
    limits = TRAVEL_POLICY["daily_budget"][region]

    if params.transportation_type:
        rule = TRAVEL_POLICY["transportation_rules"].get(params.transportation_type)
        if rule:
            if rule["allowed"]:
                results["checks"].append(
                    {"item": "交通手段", "status": "OK", "detail": f"{params.transportation_type}は利用可。{rule['note']}"}
                )
            else:
                results["errors"].append(f"{params.transportation_type}は規程上利用不可です。")
                results["status"] = "NG"
        else:
            results["warnings"].append(f"{params.transportation_type}は規程に明記されていません。要確認。")
            if results["status"] == "OK":
                results["status"] = "注意"

    if params.transportation_cost is not None:
        limit = limits["transportation"]
        if params.transportation_cost <= limit:
            results["checks"].append(
                {"item": "交通費", "status": "OK", "detail": f"交通費 {params.transportation_cost:,}円は上限 {limit:,}円以内です。"}
            )
        else:
            results["warnings"].append(
                f"交通費 {params.transportation_cost:,}円が上限 {limit:,}円を超えています。部長承認が必要です。"
            )
            if results["status"] == "OK":
                results["status"] = "注意"

    if params.hotel_cost_per_night is not None:
        limit = limits["accommodation"]
        if params.hotel_cost_per_night <= limit:
            results["checks"].append(
                {"item": "宿泊費", "status": "OK", "detail": f"1泊 {params.hotel_cost_per_night:,}円は上限 {limit:,}円以内です。"}
            )
        else:
            results["errors"].append(f"1泊 {params.hotel_cost_per_night:,}円が上限 {limit:,}円を超えています。")
            results["status"] = "NG"

    if params.total_budget is not None:
        results["summary"] = {
            "total_budget": params.total_budget,
            "policy_check": results["status"],
            "approval_required": results["status"] != "OK",
        }

    return results


def policy_checker_declaration() -> FunctionDeclaration:
    return FunctionDeclaration(
        name="policy_checker",
        description="社内旅費規程に照らして、出張条件が規程に適合しているかチェックします（モック）。",
        parameters={
            "type": "object",
            "properties": {
                "transportation_type": {"type": "string", "description": "交通手段タイプ（新幹線、飛行機等）"},
                "transportation_cost": {"type": "integer", "description": "交通費総額"},
                "hotel_cost_per_night": {"type": "integer", "description": "1泊あたりの宿泊費"},
                "total_nights": {"type": "integer", "description": "宿泊数"},
                "total_budget": {"type": "integer", "description": "総予算"},
                "is_domestic": {"type": "boolean", "description": "国内出張かどうか"},
            },
        },
    )

