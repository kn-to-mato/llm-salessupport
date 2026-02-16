"""Travel support agent powered by Vertex AI (Gemini) tool calling.

This module intentionally contains **no** LLM Observability / APM instrumentation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import vertexai
from vertexai.generative_models import (
    Content,
    FunctionCall,
    GenerationConfig,
    GenerativeModel,
    Part,
    Tool,
)

from app.config import get_settings
from app.models.schemas import SessionData, TravelPlan, PlanSummary, TransportationDetail, HotelDetail
from app.agents.tools import (
    policy_checker_declaration,
    transportation_search_declaration,
    hotel_search_declaration,
    plan_generator_declaration,
    run_policy_checker,
    run_transportation_search,
    run_hotel_search,
    run_plan_generator,
)


SYSTEM_INSTRUCTION = """あなたは営業担当者の出張計画をサポートするAIアシスタントです。
ユーザーの出張希望に応じて、適切なツールを使って情報を収集し、最適なプランを提案します。

## あなたが使えるツール
1. policy_checker: 社内旅費規程をチェック（規程/予算の相談）
2. transportation_search: 交通手段を検索
3. hotel_search: ホテルを検索（宿泊が必要な場合）
4. plan_generator: 出張プランを生成（内部で交通/ホテル検索を行う）

## ツール選択のガイドライン
- 「規程」「予算」について言及 → policy_checker
- 出発地・目的地・日付が分かっている → plan_generator（推奨）
- 条件が不足 → ツールを使わずにユーザーに質問

## 重要
- プランを提案する際は、必ず plan_generator を使用してください（自作しない）。
- 日帰りの場合は return_date を省略してください。
"""


class TravelSupportAgent:
    def __init__(self) -> None:
        self.settings = get_settings()

        self._vertex_ready = False

        if self.settings.vertex_enabled:
            # Vertex AI init (ADC)
            try:
                vertexai.init(
                    project=self.settings.google_cloud_project or None,
                    location=self.settings.google_cloud_location,
                )
                self._vertex_ready = True
            except Exception as e:
                # Do not hard-fail here. We keep a fallback mode so that API compatibility
                # can be validated before setting up auth/IAM.
                self._vertex_ready = False
                self._vertex_init_error = (
                    "Vertex AI の初期化に失敗しました。"
                    " 環境変数 GOOGLE_CLOUD_PROJECT / GOOGLE_CLOUD_LOCATION を設定し、"
                    " ローカルの場合は ADC（例: `gcloud auth application-default login`）が必要です。"
                    f" (detail={type(e).__name__}: {e})"
                )
        else:
            self._vertex_ready = False
            self._vertex_init_error = "VERTEX_ENABLED=false のため Vertex AI を使用しません。"

        self._tools = Tool(
            function_declarations=[
                policy_checker_declaration(),
                transportation_search_declaration(),
                hotel_search_declaration(),
                plan_generator_declaration(),
            ]
        )

        self._model = None
        if self._vertex_ready:
            self._model = GenerativeModel(
                model_name=self.settings.vertex_model,
                system_instruction=[SYSTEM_INSTRUCTION],
            )

    async def process_message(self, user_message: str, session_data: SessionData) -> Dict[str, Any]:
        # Fallback mode (no Vertex): keep API compatible and deterministic
        if not self._vertex_ready or self._model is None:
            return self._process_message_fallback(user_message=user_message, session_data=session_data)

        # Build conversation (Vertex has no native "system" role here; we use system_instruction above)
        contents: List[Content] = []
        contents.extend(self._history_to_contents(session_data))
        contents.append(Content(role="user", parts=[Part.from_text(user_message)]))

        generation_config = GenerationConfig(temperature=0.3)

        plans: List[TravelPlan] = []

        # tool-calling loop (bounded)
        response = self._model.generate_content(
            contents=contents,
            tools=[self._tools],
            generation_config=generation_config,
        )

        for _ in range(5):
            function_calls = self._extract_function_calls(response)
            if not function_calls:
                break

            function_response_parts: List[Part] = []
            for fc in function_calls:
                result, extracted_plans = self._dispatch_tool(fc)
                if extracted_plans:
                    plans = extracted_plans
                function_response_parts.append(
                    Part.from_function_response(name=fc.name, response={"contents": result})
                )

            # Append model function call message + our function responses
            contents.append(response.candidates[0].content)
            contents.append(Content(role="user", parts=function_response_parts))

            response = self._model.generate_content(
                contents=contents,
                tools=[self._tools],
                generation_config=generation_config,
            )

        text = getattr(response, "text", None) or self._safe_text(response) or "承知しました。条件をもう少し教えてください。"
        return {"response": text, "plans": plans, "updated_conditions": session_data.conditions}

    def _process_message_fallback(self, user_message: str, session_data: SessionData) -> Dict[str, Any]:
        """Minimal deterministic fallback when Vertex isn't configured yet.

        - Keeps the API running so frontend compatibility/tests can proceed.
        - Does NOT attempt to be smart; it uses simple heuristics + mock tools.
        """
        text = user_message.strip()
        plans: List[TravelPlan] = []

        lowered = text.lower()
        mentions_budget = ("予算" in text) or ("規程" in text) or ("ルール" in text)

        # If it looks like a plan request with enough info, try plan_generator with defaults.
        # This is intentionally simplistic.
        has_departure = any(k in text for k in ["東京", "大阪", "名古屋", "福岡", "仙台"])
        has_date_hint = any(k in text for k in ["月", "日", "出発", "帰着", "日帰り"])

        if mentions_budget:
            _ = run_policy_checker(is_domestic=True)
            response = (
                "規程チェックは可能です。"
                "出発地・目的地・日程・交通手段（希望）・宿泊有無・予算（あれば）を教えてください。"
                " それに基づいて規程観点で注意点も含めて提案します。"
            )
            return {"response": response, "plans": plans, "updated_conditions": session_data.conditions}

        if has_departure and has_date_hint:
            # crude defaults: try to infer destination pair if mentioned
            departure = "東京" if "東京" in text else "大阪" if "大阪" in text else "東京"
            destination = "大阪" if "大阪" in text and departure != "大阪" else "名古屋" if "名古屋" in text else "福岡" if "福岡" in text else "大阪"

            # default dates (demo): fixed upcoming dates
            depart_date = "2026-12-15"
            return_date = None if ("日帰り" in text) else "2026-12-16"

            out = run_plan_generator(
                departure_location=departure,
                destination=destination,
                depart_date=depart_date,
                return_date=return_date,
            )
            plans = self._convert_plans(out.get("plans", []) or [])
            response = "条件が一部不明なため、デモ用の仮条件でプランを生成しました。必要なら出発地・目的地・日程を正確に教えてください。"
            return {"response": response, "plans": plans, "updated_conditions": session_data.conditions}

        response = (
            "出張計画を作ります。"
            "出発地、目的地、出発日（YYYY-MM-DD）、帰着日（任意）、希望交通手段、予算（任意）を教えてください。"
            f"（注: いまはVertex AI未設定のフォールバックモードです: {getattr(self, '_vertex_init_error', 'unknown')}）"
        )
        return {"response": response, "plans": plans, "updated_conditions": session_data.conditions}

    def _history_to_contents(self, session_data: SessionData) -> List[Content]:
        # Use last 10 messages
        contents: List[Content] = []
        for msg in session_data.messages[-10:]:
            if msg.role == "user":
                contents.append(Content(role="user", parts=[Part.from_text(msg.content)]))
            elif msg.role == "assistant":
                contents.append(Content(role="model", parts=[Part.from_text(msg.content)]))
        return contents

    def _extract_function_calls(self, response) -> List[FunctionCall]:
        try:
            cand = response.candidates[0]
            # Vertex SDK exposes function_calls directly on candidate in examples
            return list(getattr(cand, "function_calls", []) or [])
        except Exception:
            return []

    def _dispatch_tool(self, fc: FunctionCall) -> Tuple[Dict[str, Any], List[TravelPlan]]:
        name = fc.name
        args = dict(fc.args or {})

        plans: List[TravelPlan] = []

        if name == "policy_checker":
            return run_policy_checker(**args), plans
        if name == "transportation_search":
            return run_transportation_search(**args), plans
        if name == "hotel_search":
            return run_hotel_search(**args), plans
        if name == "plan_generator":
            out = run_plan_generator(**args)
            plans = self._convert_plans(out.get("plans", []) or [])
            return out, plans

        return {"error": f"Unknown tool: {name}"}, plans

    def _convert_plans(self, raw_plans: List[Dict[str, Any]]) -> List[TravelPlan]:
        converted: List[TravelPlan] = []
        for p in raw_plans:
            try:
                converted.append(
                    TravelPlan(
                        plan_id=p.get("plan_id", ""),
                        label=p.get("label", ""),
                        summary=PlanSummary(**(p.get("summary") or {})),
                        outbound_transportation=TransportationDetail(**p["outbound_transportation"])
                        if p.get("outbound_transportation")
                        else None,
                        return_transportation=TransportationDetail(**p["return_transportation"])
                        if p.get("return_transportation")
                        else None,
                        hotel=HotelDetail(**p["hotel"]) if p.get("hotel") else None,
                    )
                )
            except Exception:
                # keep going even if a single plan has shape issues
                continue
        return converted

    def _safe_text(self, response) -> Optional[str]:
        try:
            cand = response.candidates[0]
            parts = cand.content.parts or []
            for part in parts:
                if getattr(part, "text", None):
                    return part.text
        except Exception:
            return None
        return None

