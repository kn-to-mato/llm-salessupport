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
import time
from typing import Any, Dict, List, Optional

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
# プロンプトテンプレート（シンプル化）
# =============================================================================

SYSTEM_PROMPT = """あなたは営業担当者の出張計画をサポートするAIアシスタントです。
ユーザーの出張希望に応じて、適切なツールを使って情報を収集し、最適なプランを提案します。

## あなたが使えるツール
1. **policy_checker**: 社内旅費規程をチェックします。予算や規程について質問された場合に使用してください。
2. **transportation_search**: 交通手段（新幹線、飛行機など）を検索します。出発地・目的地・日付がわかったら使用してください。
3. **hotel_search**: 宿泊施設を検索します。宿泊が必要な場合（日帰りでない場合）に使用してください。
4. **plan_generator**: 出発地・目的地・日程が揃ったら、交通・宿泊を組み合わせてプランを生成します。

## ツール選択のガイドライン
- ユーザーが「規程」「予算」について言及した場合 → policy_checker を使う
- 出発地・目的地・日付がわかっている場合 → **必ず plan_generator を呼び出す**
- 日帰りの場合 → plan_generator に return_date を省略して渡す
- 条件が不足している場合 → ツールを使わずにユーザーに質問

## 現在の会話状況
{context}

## 重要
- **プランを提案する際は、必ず plan_generator ツールを使用してください。自分でプランを生成してはいけません。**
- 条件が不足している場合は、まずユーザーに確認してください
- 日帰り出張の場合、hotel_search は使用しないでください
- 会話の中で条件が揃ったら、すぐに plan_generator を呼び出してください
- 「お願いします」「それでお願い」などの確認が来たら、条件が揃っていれば plan_generator を呼び出してください
"""


class TravelSupportAgent:
    """出張サポートエージェント（簡素化版）
    
    AgentExecutor にツール選択を完全に委譲し、
    冗長な条件抽出ロジックを削除。
    """

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
        company_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """ユーザーメッセージを処理
        
        LLM が自律的にツールを選択・実行:
        - policy_checker: 規程チェック（予算・規程について言及された場合）
        - transportation_search: 交通検索（個別に呼び出された場合）
        - hotel_search: ホテル検索（個別に呼び出された場合）
        - plan_generator: プラン生成（条件が揃っている場合）
        
        入力によって呼ばれるツール数は変動（0〜4つ）
        """
        start_time = time.time()

        # === LLMObs: Agentスパンを開始 ===
        with LLMObs.agent(
            name="travel-support-agent",
            session_id=session_data.session_id,
        ) as agent_span:
            # タグを構築（会社名がある場合は追加）
            custom_tags = {}
            if company_name:
                custom_tags["company_name"] = company_name
            custom_tags["user_id"] = session_data.user_id
            
            LLMObs.annotate(
                span=agent_span,
                input_data={
                    "user_message": user_message,
                    "history_count": len(session_data.messages),
                    "version": APP_VERSION,
                },
                tags=custom_tags,
            )

            logger.info(
                "process_message_start",
                session_id=session_data.session_id,
                message_length=len(user_message),
                history_count=len(session_data.messages),
            )

            try:
                # 会話履歴を構築
                chat_history = self._build_chat_history(session_data.messages)

                # コンテキストを構築
                context = self._build_context(session_data)

                # === AgentExecutor を実行 ===
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
                    })

                    agent_output = result.get("output", "")

                    # ツール呼び出しをログ
                    tools_called = self._extract_tools_called(result)

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

                # プランを抽出
                plans = self._extract_plans_from_result(result)

                total_duration = time.time() - start_time

                # Agentスパンの出力をアノテート
                LLMObs.annotate(
                    span=agent_span,
                    output_data={
                        "response": agent_output[:200] if len(agent_output) > 200 else agent_output,
                        "tools_called": tools_called,
                        "plans_generated": len(plans),
                        "duration_ms": round(total_duration * 1000, 2),
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
                    "updated_conditions": session_data.conditions,
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

    def _build_chat_history(self, messages: List[Message]) -> List:
        """会話履歴をLangChain形式に変換"""
        chat_history = []
        for msg in messages[-10:]:  # 直近10件
            if msg.role == "user":
                chat_history.append(HumanMessage(content=msg.content))
            else:
                chat_history.append(AIMessage(content=msg.content))
        return chat_history

    def _build_context(self, session_data: SessionData) -> str:
        """コンテキスト情報を構築"""
        parts = []

        if session_data.plans:
            parts.append(f"生成済みプラン数: {len(session_data.plans)}")

        msg_count = len(session_data.messages)
        parts.append(f"会話ターン数: {msg_count}")

        # 条件がある場合は表示
        conditions = session_data.conditions
        if conditions.departure_location:
            parts.append(f"出発地: {conditions.departure_location}")
        if conditions.destination:
            parts.append(f"目的地: {conditions.destination}")
        if conditions.depart_date:
            parts.append(f"出発日: {conditions.depart_date}")
        if conditions.return_date:
            parts.append(f"帰着日: {conditions.return_date}")

        return "\n".join(parts) if parts else "新規会話"

    def _extract_tools_called(self, result: Dict) -> List[str]:
        """実行されたツールを抽出"""
        tools_called = []
        intermediate_steps = result.get("intermediate_steps", [])
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
        return tools_called

    def _extract_plans_from_result(self, result: Dict) -> List[TravelPlan]:
        """エージェントの実行結果からプランを抽出
        
        plan_generator ツールの実行結果からプランを取得
        """
        import json
        
        plans = []
        intermediate_steps = result.get("intermediate_steps", [])

        for step in intermediate_steps:
            if len(step) >= 2:
                action = step[0]
                tool_output = step[1]
                tool_name = getattr(action, 'tool', '')

                if tool_name == "plan_generator":
                    # tool_output が文字列の場合はJSONとしてパース
                    if isinstance(tool_output, str):
                        try:
                            tool_output = json.loads(tool_output)
                        except json.JSONDecodeError:
                            logger.warning("plan_generator_output_not_json", output=tool_output[:100])
                            continue
                    
                    if isinstance(tool_output, dict):
                        raw_plans = tool_output.get("plans", [])
                        logger.info("plan_generator_plans_found", count=len(raw_plans))
                        
                        for p in raw_plans:
                            if isinstance(p, dict):
                                try:
                                    plan = TravelPlan(
                                        plan_id=p.get("plan_id", ""),
                                        label=p.get("label", ""),
                                        summary=PlanSummary(
                                            depart_date=p.get("summary", {}).get("depart_date", ""),
                                            return_date=p.get("summary", {}).get("return_date", ""),
                                            destination=p.get("summary", {}).get("destination", ""),
                                            transportation=p.get("summary", {}).get("transportation", ""),
                                            hotel=p.get("summary", {}).get("hotel", ""),
                                            estimated_total=p.get("summary", {}).get("estimated_total", 0),
                                            policy_status=p.get("summary", {}).get("policy_status", "OK"),
                                            policy_note=p.get("summary", {}).get("policy_note"),
                                        ),
                                        outbound_transportation=TransportationDetail(
                                            **p["outbound_transportation"]
                                        ) if p.get("outbound_transportation") else None,
                                        return_transportation=TransportationDetail(
                                            **p["return_transportation"]
                                        ) if p.get("return_transportation") else None,
                                        hotel=HotelDetail(**p["hotel"]) if p.get("hotel") else None,
                                    )
                                    plans.append(plan)
                                    logger.info("plan_extracted", plan_id=plan.plan_id, label=plan.label)
                                except Exception as e:
                                    logger.warning(
                                        "plan_extraction_error",
                                        error=str(e),
                                        plan_data=str(p)[:200],
                                    )

        logger.info("total_plans_extracted", count=len(plans))
        return plans
