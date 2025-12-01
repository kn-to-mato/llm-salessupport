"""出張サポートAIエージェント"""
import json
import time
from typing import Any, Dict, List
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

from app.config import get_settings
from app.logging_config import get_logger
from app.models.schemas import (
    TravelConditions, 
    TravelPlan, 
    SessionData,
    Message,
    PlanSummary,
    TransportationDetail,
    HotelDetail,
)
from .tools import (
    PolicyCheckerTool,
    TransportationSearchTool,
    HotelSearchTool,
    PlanGeneratorTool,
)

settings = get_settings()
logger = get_logger(__name__)


SYSTEM_PROMPT = """あなたは営業担当者の出張計画をサポートするAIアシスタントです。
ユーザーが出張の希望を伝えると、以下の流れでサポートします：

1. **条件の確認**: 出発地、目的地、日程、予算などを確認
2. **規程チェック**: 社内旅費規程に照らして条件を確認
3. **交通手段の検索**: 新幹線・飛行機などの候補を検索
4. **宿泊先の検索**: ビジネスホテルの候補を検索
5. **プランの提示**: 複数のプラン案をまとめて提示

## 重要なルール

- 必要な情報が揃っていない場合は、丁寧に質問してください
- 規程に違反する可能性がある場合は、その旨を伝えてください
- プランは必ず複数案（2〜3案）を提示してください
- 金額は具体的な数字を示してください

## 現在の会話状況
{context}

## 抽出済みの条件
{conditions}
"""


class TravelSupportAgent:
    """出張サポートエージェント"""
    
    def __init__(self):
        logger.info(
            "travel_agent_init_start",
            model=settings.openai_model,
        )
        
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0.3,
            api_key=settings.openai_api_key,
        )
        
        logger.debug(
            "llm_initialized",
            model=settings.openai_model,
            temperature=0.3,
        )
        
        # ツールの初期化
        self.tools = [
            PolicyCheckerTool(),
            TransportationSearchTool(),
            HotelSearchTool(),
            PlanGeneratorTool(),
        ]
        
        logger.debug(
            "tools_initialized",
            tool_count=len(self.tools),
            tool_names=[t.name for t in self.tools],
        )
        
        # プロンプトテンプレート
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # エージェントの作成
        self.agent = create_openai_tools_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.prompt,
        )
        
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=10,
        )
        
        logger.info(
            "travel_agent_init_complete",
            max_iterations=10,
        )
    
    async def process_message(
        self,
        user_message: str,
        session_data: SessionData,
    ) -> Dict[str, Any]:
        """ユーザーメッセージを処理"""
        start_time = time.time()
        
        logger.info(
            "process_message_start",
            session_id=session_data.session_id,
            message_length=len(user_message),
            history_count=len(session_data.messages),
        )
        
        # 会話履歴をLangChain形式に変換
        chat_history = self._convert_messages_to_langchain(session_data.messages)
        logger.debug(
            "chat_history_converted",
            history_length=len(chat_history),
        )
        
        # コンテキスト情報
        context = self._build_context(session_data)
        conditions = self._format_conditions(session_data.conditions)
        
        logger.debug(
            "context_built",
            context=context,
            conditions_formatted=conditions[:200] + "..." if len(conditions) > 200 else conditions,
        )
        
        try:
            # エージェントを実行
            logger.info(
                "agent_executor_invoke_start",
                session_id=session_data.session_id,
            )
            
            agent_start = time.time()
            result = await self.agent_executor.ainvoke({
                "input": user_message,
                "chat_history": chat_history,
                "context": context,
                "conditions": conditions,
            })
            agent_duration = time.time() - agent_start
            
            logger.info(
                "agent_executor_invoke_complete",
                session_id=session_data.session_id,
                duration_ms=round(agent_duration * 1000, 2),
                output_length=len(result.get("output", "")),
            )
            
            # レスポンスを解析
            output = result.get("output", "")
            
            logger.debug(
                "agent_output",
                output_preview=output[:500] + "..." if len(output) > 500 else output,
            )
            
            # プラン生成が含まれているか確認
            plans = self._extract_plans_from_context(result)
            
            # 条件を更新
            logger.debug(
                "condition_extraction_start",
                session_id=session_data.session_id,
            )
            
            extract_start = time.time()
            updated_conditions = await self._update_conditions(
                user_message, 
                session_data.conditions
            )
            extract_duration = time.time() - extract_start
            
            logger.debug(
                "condition_extraction_complete",
                session_id=session_data.session_id,
                duration_ms=round(extract_duration * 1000, 2),
            )
            
            total_duration = time.time() - start_time
            logger.info(
                "process_message_complete",
                session_id=session_data.session_id,
                total_duration_ms=round(total_duration * 1000, 2),
            )
            
            return {
                "response": output,
                "plans": plans,
                "updated_conditions": updated_conditions,
            }
            
        except Exception as e:
            logger.error(
                "process_message_error",
                session_id=session_data.session_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            return {
                "response": f"申し訳ありません。処理中にエラーが発生しました: {str(e)}",
                "plans": [],
                "updated_conditions": session_data.conditions,
            }
    
    async def _update_conditions(
        self,
        user_message: str,
        current_conditions: TravelConditions
    ) -> TravelConditions:
        """ユーザーメッセージから条件を更新"""
        logger.debug(
            "update_conditions_start",
            message_length=len(user_message),
            current_departure=current_conditions.departure_location,
            current_destination=current_conditions.destination,
        )
        
        extraction_prompt = f"""
以下のユーザーメッセージから出張条件を抽出してJSON形式で返してください。
抽出できない項目はnullとしてください。

ユーザーメッセージ: {user_message}

現在の条件:
{current_conditions.model_dump_json(indent=2)}

以下のJSON形式で返してください（コードブロックなしで）:
{{
    "departure_location": "出発地（東京など）",
    "destination": "目的地（大阪など）",
    "depart_date": "出発日（YYYY-MM-DD形式）",
    "return_date": "帰着日（YYYY-MM-DD形式）",
    "budget": 予算（数値、円単位）,
    "preferred_transportation": "希望交通手段（新幹線、飛行機など）",
    "purpose": "出張目的",
    "notes": "その他要望"
}}
"""
        try:
            logger.debug("llm_extraction_invoke_start")
            
            extract_start = time.time()
            response = await self.llm.ainvoke([HumanMessage(content=extraction_prompt)])
            extract_duration = time.time() - extract_start
            
            logger.debug(
                "llm_extraction_invoke_complete",
                duration_ms=round(extract_duration * 1000, 2),
                response_length=len(response.content),
            )
            
            content = response.content.strip()
            
            # JSONを抽出
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            logger.debug(
                "json_parsing",
                content_preview=content[:200] + "..." if len(content) > 200 else content,
            )
            
            extracted = json.loads(content)
            
            # 現在の条件とマージ
            updated = current_conditions.model_dump()
            changes = []
            for key, value in extracted.items():
                if value is not None and value != "null" and value != updated.get(key):
                    changes.append(f"{key}: {updated.get(key)} -> {value}")
                    updated[key] = value
            
            if changes:
                logger.info(
                    "conditions_changes_detected",
                    changes=changes,
                )
            else:
                logger.debug("no_condition_changes")
            
            return TravelConditions(**updated)
            
        except Exception as e:
            logger.warning(
                "condition_extraction_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            return current_conditions
    
    async def generate_plans(
        self,
        conditions: TravelConditions,
    ) -> List[TravelPlan]:
        """条件からプランを生成"""
        logger.info(
            "generate_plans_start",
            departure=conditions.departure_location,
            destination=conditions.destination,
            depart_date=conditions.depart_date,
            return_date=conditions.return_date,
            budget=conditions.budget,
            preferred_transportation=conditions.preferred_transportation,
        )
        
        if not all([
            conditions.departure_location,
            conditions.destination,
            conditions.depart_date,
            conditions.return_date,
        ]):
            logger.warning(
                "generate_plans_incomplete_conditions",
                has_departure=bool(conditions.departure_location),
                has_destination=bool(conditions.destination),
                has_depart_date=bool(conditions.depart_date),
                has_return_date=bool(conditions.return_date),
            )
            return []
        
        # 交通手段を検索
        logger.debug(
            "transportation_search_start",
            departure=conditions.departure_location,
            destination=conditions.destination,
        )
        
        trans_tool = TransportationSearchTool()
        trans_start = time.time()
        trans_result = trans_tool._run(
            departure=conditions.departure_location,
            destination=conditions.destination,
            preferred_type=conditions.preferred_transportation,
        )
        trans_duration = time.time() - trans_start
        
        logger.debug(
            "transportation_search_complete",
            duration_ms=round(trans_duration * 1000, 2),
            found=trans_result.get("found", False),
            option_count=len(trans_result.get("options", [])),
        )
        
        if trans_result.get("options"):
            for opt in trans_result["options"]:
                logger.debug(
                    "transportation_option",
                    type=opt.get("type"),
                    train_name=opt.get("train_name"),
                    schedule_count=len(opt.get("schedules", [])),
                )
        
        # ホテルを検索
        hotel_tool = HotelSearchTool()
        
        # 宿泊数を計算
        try:
            dep = datetime.strptime(conditions.depart_date, "%Y-%m-%d")
            ret = datetime.strptime(conditions.return_date, "%Y-%m-%d")
            nights = (ret - dep).days
        except:
            nights = 1
        
        logger.debug(
            "hotel_search_start",
            destination=conditions.destination,
            nights=nights,
        )
        
        hotel_start = time.time()
        hotel_result = hotel_tool._run(
            destination=conditions.destination,
            nights=nights,
            max_price_per_night=15000,  # 規程上限
        )
        hotel_duration = time.time() - hotel_start
        
        logger.debug(
            "hotel_search_complete",
            duration_ms=round(hotel_duration * 1000, 2),
            found=hotel_result.get("found", False),
            hotel_count=len(hotel_result.get("hotels", [])),
        )
        
        if hotel_result.get("hotels"):
            for h in hotel_result["hotels"]:
                logger.debug(
                    "hotel_option",
                    name=h.get("name"),
                    area=h.get("area"),
                    price_per_night=h.get("price_per_night"),
                    rating=h.get("rating"),
                )
        
        # プランを生成
        logger.debug("plan_generation_tool_start")
        
        plan_tool = PlanGeneratorTool()
        plan_start = time.time()
        plan_result = plan_tool._run(
            departure_location=conditions.departure_location,
            destination=conditions.destination,
            depart_date=conditions.depart_date,
            return_date=conditions.return_date,
            transportation_options=trans_result.get("options", []),
            hotel_options=hotel_result.get("hotels", []),
            budget=conditions.budget,
        )
        plan_duration = time.time() - plan_start
        
        logger.debug(
            "plan_generation_tool_complete",
            duration_ms=round(plan_duration * 1000, 2),
            success=plan_result.get("success", False),
            plan_count=plan_result.get("total_plans", 0),
        )
        
        # TravelPlanオブジェクトに変換
        plans = []
        for p in plan_result.get("plans", []):
            logger.debug(
                "converting_plan",
                plan_id=p["plan_id"],
                label=p["label"],
                estimated_total=p["summary"]["estimated_total"],
                policy_status=p["summary"]["policy_status"],
            )
            
            plan = TravelPlan(
                plan_id=p["plan_id"],
                label=p["label"],
                summary=PlanSummary(**p["summary"]),
                outbound_transportation=TransportationDetail(**p["outbound_transportation"]) if p.get("outbound_transportation") else None,
                return_transportation=TransportationDetail(**p["return_transportation"]) if p.get("return_transportation") else None,
                hotel=HotelDetail(**p["hotel"]) if p.get("hotel") else None,
            )
            plans.append(plan)
        
        logger.info(
            "generate_plans_complete",
            total_plans=len(plans),
            plan_summaries=[
                {
                    "label": p.label,
                    "total": p.summary.estimated_total,
                    "status": p.summary.policy_status
                }
                for p in plans
            ],
        )
        
        return plans
    
    def _convert_messages_to_langchain(self, messages: List[Message]) -> List:
        """メッセージをLangChain形式に変換"""
        lc_messages = []
        for msg in messages:
            if msg.role == "user":
                lc_messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                lc_messages.append(AIMessage(content=msg.content))
        return lc_messages
    
    def _build_context(self, session_data: SessionData) -> str:
        """コンテキスト情報を構築"""
        context_parts = []
        
        if session_data.plans:
            context_parts.append(f"生成済みプラン数: {len(session_data.plans)}")
        
        msg_count = len(session_data.messages)
        context_parts.append(f"会話ターン数: {msg_count}")
        
        return "\n".join(context_parts) if context_parts else "新規会話"
    
    def _format_conditions(self, conditions: TravelConditions) -> str:
        """条件を文字列形式にフォーマット"""
        parts = []
        
        if conditions.departure_location:
            parts.append(f"- 出発地: {conditions.departure_location}")
        if conditions.destination:
            parts.append(f"- 目的地: {conditions.destination}")
        if conditions.depart_date:
            parts.append(f"- 出発日: {conditions.depart_date}")
        if conditions.return_date:
            parts.append(f"- 帰着日: {conditions.return_date}")
        if conditions.budget:
            parts.append(f"- 予算: {conditions.budget:,}円")
        if conditions.preferred_transportation:
            parts.append(f"- 希望交通手段: {conditions.preferred_transportation}")
        if conditions.purpose:
            parts.append(f"- 目的: {conditions.purpose}")
        if conditions.notes:
            parts.append(f"- 備考: {conditions.notes}")
        
        return "\n".join(parts) if parts else "まだ条件が確認できていません"
    
    def _extract_plans_from_context(self, result: Dict) -> List[TravelPlan]:
        """エージェントの実行結果からプランを抽出"""
        # この実装では、intermediate_stepsからプラン生成ツールの結果を探す
        # 実際のプラン生成はgenerate_plansメソッドで行う
        return []
