"""出張サポートAIエージェント

LangChain AgentExecutor を使用した自律的なツール選択:
- LLMがユーザー入力を分析し、必要なツールを自律的に選択・実行
- 入力によって呼ばれるツール数が変動（0〜4つ）

利用可能なツール:
1. policy_checker - 社内旅費規程チェック
2. transportation_search - 交通手段検索
3. hotel_search - 宿泊施設検索
4. plan_generator - 出張プラン生成
"""
import json
import time
from typing import Any, Dict, List, Optional
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

# Datadog LLM Observability SDK
from ddtrace.llmobs import LLMObs

from app.config import get_settings, APP_VERSION
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


# =============================================================================
# プロンプトテンプレート
# =============================================================================

# LangChain AgentExecutor用システムプロンプト
SYSTEM_PROMPT = """あなたは営業担当者の出張計画をサポートするAIアシスタントです。
ユーザーの出張希望に応じて、適切なツールを使って情報を収集し、最適なプランを提案します。

## あなたが使えるツール
1. **policy_checker**: 社内旅費規程をチェックします。予算や規程について質問された場合に使用してください。
2. **transportation_search**: 交通手段（新幹線、飛行機など）を検索します。出発地・目的地・日付がわかったら使用してください。
3. **hotel_search**: 宿泊施設を検索します。宿泊が必要な場合（日帰りでない場合）に使用してください。
4. **plan_generator**: 交通・宿泊情報を組み合わせて出張プランを生成します。交通検索の後に使用してください。

## ツール選択のガイドライン
- ユーザーが「規程」「予算」について言及した場合 → policy_checker を使う
- 出発地・目的地・日付がわかっている場合 → transportation_search を使う
- 宿泊が必要な場合（日帰りでない場合） → hotel_search を使う
- 交通・宿泊情報が揃ったら → plan_generator でプランを作成
- 日帰りの場合 → hotel_search はスキップ
- 条件が不足している場合 → ツールを使わずにユーザーに質問

## 現在の会話状況
{context}

## 抽出済みの条件
{conditions}

## 重要
- 必要なツールだけを選んで使用してください
- 日帰り出張の場合、hotel_search は使用しないでください
- 条件が不足している場合は、まずユーザーに確認してください
"""

# LLM#1: 条件抽出
CONDITION_EXTRACTION_PROMPT = """以下のユーザーメッセージから出張条件を抽出してJSON形式で返してください。
抽出できない項目はnullとしてください。

ユーザーメッセージ: {user_message}

現在の条件:
{current_conditions}

以下のJSON形式で返してください（コードブロックなしで）:
{{
    "departure_location": "出発地（東京など）",
    "destination": "目的地（大阪など）",
    "depart_date": "出発日（YYYY-MM-DD形式）",
    "return_date": "帰着日（YYYY-MM-DD形式、日帰りの場合はnull）",
    "budget": 予算（数値、円単位）,
    "preferred_transportation": "希望交通手段（新幹線、飛行機など）",
    "purpose": "出張目的",
    "notes": "その他要望",
    "is_day_trip": true/false（日帰りかどうか）,
    "needs_policy_check": true/false（規程チェックが必要か）
}}
"""

# LLM#2: 規程チェック
POLICY_VALIDATION_PROMPT = """以下の出張条件について、社内旅費規程に適合しているか確認してください。

## 社内旅費規程
- 交通費: 新幹線普通車またはビジネスクラス以下の航空券
- 宿泊費: 1泊あたり15,000円まで（東京23区・大阪市内は18,000円まで）
- 日当: 国内出張は1日あたり2,500円
- 出張期間: 原則として業務に必要な最短期間

## 出張条件
{conditions}

以下のJSON形式で回答してください:
{{
    "is_compliant": true/false,
    "compliance_status": "適合" または "要確認" または "規程違反の可能性",
    "warnings": ["注意事項1", "注意事項2"],
    "recommendations": ["推奨事項1", "推奨事項2"],
    "estimated_budget": {{
        "transportation": 概算交通費,
        "accommodation": 概算宿泊費,
        "daily_allowance": 概算日当,
        "total": 合計概算
    }}
}}
"""

# LLM#3: プラン最適化
PLAN_OPTIMIZATION_PROMPT = """以下の検索結果を基に、最適な出張プランを3案提案してください。

## 出張条件
{conditions}

## 規程チェック結果
{policy_result}

## 交通検索結果
{transportation_result}

## ホテル検索結果
{hotel_result}

以下のJSON形式で3つのプランを提案してください:
{{
    "plans": [
        {{
            "plan_id": "plan_1",
            "label": "コスパ重視プラン",
            "description": "プランの説明",
            "transportation": {{
                "outbound": "往路の詳細",
                "return": "復路の詳細",
                "total_cost": 交通費合計
            }},
            "hotel": {{
                "name": "ホテル名",
                "nights": 宿泊数,
                "total_cost": 宿泊費合計
            }},
            "total_cost": 総額,
            "recommendation_reason": "このプランをおすすめする理由"
        }}
    ]
}}
"""

# LLM#4: 最終回答生成
RESPONSE_SYNTHESIS_PROMPT = """以下の情報を基に、ユーザーへの最終回答を生成してください。
丁寧で分かりやすい日本語で回答してください。

## ユーザーの依頼
{user_message}

## 抽出された条件
{conditions}

## 規程チェック結果
{policy_result}

## 提案プラン
{plans}

## 会話履歴
{chat_history}

回答のポイント:
- 条件が不足している場合は、足りない情報を質問してください
- プランがある場合は、各プランの特徴を簡潔に説明してください
- 規程に関する注意事項があれば伝えてください
- 親しみやすく、プロフェッショナルなトーンで
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
        """ユーザーメッセージを処理（AgentExecutor ベース）
        
        LLM が自律的にツールを選択・実行:
        - policy_checker: 規程チェック（予算・規程について言及された場合）
        - transportation_search: 交通検索（出発地・目的地・日付がある場合）
        - hotel_search: ホテル検索（宿泊が必要な場合）
        - plan_generator: プラン生成（交通情報がある場合）
        
        入力によって呼ばれるツール数は変動（0〜4つ）
        """
        start_time = time.time()
        
        # === LLMObs: Agentスパンを開始 ===
        with LLMObs.agent(
            name="travel-support-agent",
            session_id=session_data.session_id,
        ) as agent_span:
            LLMObs.annotate(
                span=agent_span,
                input_data={
                    "user_message": user_message,
                    "history_count": len(session_data.messages),
                    "current_conditions": session_data.conditions.model_dump(),
                    "version": APP_VERSION,
                },
            )
            
            logger.info(
                "process_message_start",
                session_id=session_data.session_id,
                message_length=len(user_message),
                history_count=len(session_data.messages),
            )
            
            try:
                # 会話履歴を構築
                chat_history = []
                for msg in session_data.messages[-10:]:  # 直近10件
                    if msg.role == "user":
                        chat_history.append(HumanMessage(content=msg.content))
                    else:
                        chat_history.append(AIMessage(content=msg.content))
                
                # 現在の条件を文字列化
                conditions_str = self._format_conditions(session_data.conditions)
                
                # コンテキストを構築
                context = self._build_context(session_data)
                
                logger.debug(
                    "agent_executor_input",
                    input_message=user_message[:100],
                    history_count=len(chat_history),
                    conditions=conditions_str[:200],
                )
                
                # === AgentExecutor を実行 ===
                # LLM が自律的にツールを選択・実行
                with LLMObs.workflow(name="agent_execution") as exec_span:
                    LLMObs.annotate(
                        span=exec_span,
                        input_data={
                            "user_message": user_message,
                            "available_tools": [t.name for t in self.tools],
                        },
                    )
                    
                    result = await self.agent_executor.ainvoke({
                        "input": user_message,
                        "chat_history": chat_history,
                        "context": context,
                        "conditions": conditions_str,
                    })
                    
                    agent_output = result.get("output", "")
                    
                    # 中間ステップ（ツール呼び出し）をログ
                    intermediate_steps = result.get("intermediate_steps", [])
                    tools_called = []
                    for step in intermediate_steps:
                        if len(step) >= 2:
                            action = step[0]
                            tool_name = getattr(action, 'tool', 'unknown')
                            tools_called.append(tool_name)
                            logger.info(
                                "tool_called",
                                tool_name=tool_name,
                                tool_input=str(getattr(action, 'tool_input', ''))[:100],
                            )
                    
                    LLMObs.annotate(
                        span=exec_span,
                        output_data={
                            "tools_called": tools_called,
                            "tools_count": len(tools_called),
                            "output_length": len(agent_output),
                        },
                    )
                    
                    logger.info(
                        "agent_execution_complete",
                        tools_called=tools_called,
                        tools_count=len(tools_called),
                    )
                
                # 条件を更新（エージェントの出力から抽出）
                updated_conditions = await self._update_conditions(
                    user_message, 
                    session_data.conditions
                )
                
                # プランを抽出（エージェントがplan_generatorを呼んだ場合）
                plans = self._extract_plans_from_result(result)
                
                total_duration = time.time() - start_time
                
                # Agentスパンの出力をアノテート
                LLMObs.annotate(
                    span=agent_span,
                    output_data={
                        "response": agent_output[:200] if len(agent_output) > 200 else agent_output,
                        "tools_called": tools_called,
                        "tools_count": len(tools_called),
                        "plans_generated": len(plans),
                    },
                )
                
                logger.info(
                    "process_message_complete",
                    session_id=session_data.session_id,
                    total_duration_ms=round(total_duration * 1000, 2),
                    tools_called=tools_called,
                )
                
                return {
                    "response": agent_output,
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
    
    # =========================================================================
    # 4段階フロー用の新しいメソッド
    # =========================================================================
    
    async def _extract_conditions_v2(
        self,
        user_message: str,
        current_conditions: TravelConditions,
    ) -> Dict[str, Any]:
        """Step 1: 条件抽出 (LLM#1)"""
        prompt = CONDITION_EXTRACTION_PROMPT.format(
            user_message=user_message,
            current_conditions=current_conditions.model_dump_json(indent=2),
        )
        
        response = await self.llm.ainvoke([HumanMessage(content=prompt)])
        content = response.content.strip()
        
        # JSONを抽出
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        try:
            extracted = json.loads(content)
        except json.JSONDecodeError:
            extracted = {}
        
        # 条件をマージ
        updated = current_conditions.model_dump()
        for key, value in extracted.items():
            if key in updated and value is not None and value != "null":
                updated[key] = value
        
        return {
            "conditions": TravelConditions(**{k: v for k, v in updated.items() if k in TravelConditions.model_fields}),
            "is_day_trip": extracted.get("is_day_trip", False),
            "needs_policy_check": extracted.get("needs_policy_check", False),
        }
    
    async def _validate_policy(
        self,
        conditions: TravelConditions,
    ) -> Dict[str, Any]:
        """Step 2: 規程チェック (LLM#2)"""
        prompt = POLICY_VALIDATION_PROMPT.format(
            conditions=conditions.model_dump_json(indent=2),
        )
        
        response = await self.llm.ainvoke([HumanMessage(content=prompt)])
        content = response.content.strip()
        
        # JSONを抽出
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            result = {
                "is_compliant": True,
                "compliance_status": "確認中",
                "warnings": [],
                "recommendations": [],
            }
        
        return result
    
    async def _optimize_plans(
        self,
        conditions: TravelConditions,
        policy_result: Optional[Dict],
        trans_result: Dict,
        hotel_result: Dict,
    ) -> Dict[str, Any]:
        """Step 3: プラン最適化 (LLM#3)"""
        prompt = PLAN_OPTIMIZATION_PROMPT.format(
            conditions=conditions.model_dump_json(indent=2),
            policy_result=json.dumps(policy_result, ensure_ascii=False, indent=2) if policy_result else "なし",
            transportation_result=json.dumps(trans_result, ensure_ascii=False, indent=2),
            hotel_result=json.dumps(hotel_result, ensure_ascii=False, indent=2),
        )
        
        response = await self.llm.ainvoke([HumanMessage(content=prompt)])
        content = response.content.strip()
        
        # JSONを抽出
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            result = {"plans": []}
        
        return result
    
    async def _synthesize_response(
        self,
        user_message: str,
        conditions: TravelConditions,
        policy_result: Optional[Dict],
        plan_result: Optional[Dict],
        chat_history: str,
    ) -> str:
        """Step 4: 最終回答生成 (LLM#4)"""
        prompt = RESPONSE_SYNTHESIS_PROMPT.format(
            user_message=user_message,
            conditions=conditions.model_dump_json(indent=2),
            policy_result=json.dumps(policy_result, ensure_ascii=False, indent=2) if policy_result else "規程チェック未実施",
            plans=json.dumps(plan_result, ensure_ascii=False, indent=2) if plan_result else "プラン未生成",
            chat_history=chat_history if chat_history else "なし",
        )
        
        response = await self.llm.ainvoke([HumanMessage(content=prompt)])
        return response.content.strip()
    
    def _format_chat_history(self, messages: List[Message]) -> str:
        """会話履歴を文字列形式にフォーマット"""
        if not messages:
            return ""
        
        formatted = []
        for msg in messages[-6:]:  # 直近6件のみ
            role = "ユーザー" if msg.role == "user" else "アシスタント"
            formatted.append(f"{role}: {msg.content[:100]}...")
        
        return "\n".join(formatted)
    
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
        """条件からプランを生成
        
        LLM Observability: このメソッド全体をWorkflowスパンとしてトラック
        各ツール呼び出しはToolスパンとしてネスト
        """
        # === LLMObs: Workflow - プラン生成 ===
        with LLMObs.workflow(name="plan_generation") as workflow_span:
            LLMObs.annotate(
                span=workflow_span,
                input_data={
                    "departure": conditions.departure_location,
                    "destination": conditions.destination,
                    "depart_date": conditions.depart_date,
                    "return_date": conditions.return_date,
                    "budget": conditions.budget,
                },
            )
            
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
            
            # === LLMObs: Tool - 交通手段検索 ===
            with LLMObs.tool(name="transportation_search") as tool_span:
                LLMObs.annotate(
                    span=tool_span,
                    input_data={
                        "departure": conditions.departure_location,
                        "destination": conditions.destination,
                        "preferred_type": conditions.preferred_transportation,
                    },
                )
                
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
                
                LLMObs.annotate(
                    span=tool_span,
                    output_data={
                        "found": trans_result.get("found", False),
                        "option_count": len(trans_result.get("options", [])),
                    },
                )
                
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
            
            # 宿泊数を計算
            try:
                dep = datetime.strptime(conditions.depart_date, "%Y-%m-%d")
                ret = datetime.strptime(conditions.return_date, "%Y-%m-%d")
                nights = (ret - dep).days
            except:
                nights = 1
            
            # === LLMObs: Tool - ホテル検索 ===
            with LLMObs.tool(name="hotel_search") as tool_span:
                LLMObs.annotate(
                    span=tool_span,
                    input_data={
                        "destination": conditions.destination,
                        "nights": nights,
                        "max_price_per_night": 15000,
                    },
                )
                
                logger.debug(
                    "hotel_search_start",
                    destination=conditions.destination,
                    nights=nights,
                )
                
                hotel_tool = HotelSearchTool()
                hotel_start = time.time()
                hotel_result = hotel_tool._run(
                    destination=conditions.destination,
                    nights=nights,
                    max_price_per_night=15000,  # 規程上限
                )
                hotel_duration = time.time() - hotel_start
                
                LLMObs.annotate(
                    span=tool_span,
                    output_data={
                        "found": hotel_result.get("found", False),
                        "hotel_count": len(hotel_result.get("hotels", [])),
                    },
                )
                
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
            
            # === LLMObs: Tool - プラン生成 ===
            with LLMObs.tool(name="plan_generator") as tool_span:
                LLMObs.annotate(
                    span=tool_span,
                    input_data={
                        "departure": conditions.departure_location,
                        "destination": conditions.destination,
                        "transportation_options": len(trans_result.get("options", [])),
                        "hotel_options": len(hotel_result.get("hotels", [])),
                    },
                )
                
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
                
                LLMObs.annotate(
                    span=tool_span,
                    output_data={
                        "success": plan_result.get("success", False),
                        "plan_count": plan_result.get("total_plans", 0),
                    },
                )
                
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
            
            # Workflowスパンの出力をアノテート
            LLMObs.annotate(
                span=workflow_span,
                output_data={
                    "total_plans": len(plans),
                    "plan_labels": [p.label for p in plans],
                },
            )
            
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
    
    def _extract_plans_from_result(self, result: Dict) -> List[TravelPlan]:
        """エージェントの実行結果からプランを抽出
        
        AgentExecutor の intermediate_steps から plan_generator ツールの
        実行結果を探してプランを取得する。
        """
        plans = []
        intermediate_steps = result.get("intermediate_steps", [])
        
        for step in intermediate_steps:
            if len(step) >= 2:
                action = step[0]
                tool_output = step[1]
                tool_name = getattr(action, 'tool', '')
                
                # plan_generator の結果からプランを抽出
                if tool_name == "plan_generator" and isinstance(tool_output, dict):
                    raw_plans = tool_output.get("plans", [])
                    for p in raw_plans:
                        if isinstance(p, dict):
                            try:
                                plan = TravelPlan(
                                    id=p.get("id", ""),
                                    name=p.get("name", ""),
                                    summary=PlanSummary(
                                        total_cost=p.get("summary", {}).get("total_cost", 0),
                                        total_duration=p.get("summary", {}).get("total_duration", ""),
                                        recommendation=p.get("summary", {}).get("recommendation", ""),
                                    ),
                                    transportation=TransportationDetail(
                                        type=p.get("transportation", {}).get("type", ""),
                                        departure_time=p.get("transportation", {}).get("departure_time", ""),
                                        arrival_time=p.get("transportation", {}).get("arrival_time", ""),
                                        cost=p.get("transportation", {}).get("cost", 0),
                                    ),
                                    hotel=HotelDetail(
                                        name=p.get("hotel", {}).get("name", ""),
                                        price_per_night=p.get("hotel", {}).get("price_per_night", 0),
                                        nights=p.get("hotel", {}).get("nights", 0),
                                        total_cost=p.get("hotel", {}).get("total_cost", 0),
                                    ) if p.get("hotel") else None,
                                )
                                plans.append(plan)
                            except Exception as e:
                                logger.warning(
                                    "plan_extraction_error",
                                    error=str(e),
                                )
        
        return plans
