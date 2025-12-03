# LLM Observability SDK 実装ガイド

## 概要

このドキュメントでは、Datadog LLM Observability SDKを使用して、階層的なスパン構造（Agent → Workflow → Tool）を実装する方法を説明します。

## 背景

### Auto Instrumentation vs SDK (Manual) Instrumentation

| 項目 | Auto Instrumentation | SDK Instrumentation |
|------|---------------------|---------------------|
| 導入方法 | `ddtrace-run` でラップ | コードにデコレータ/コンテキストマネージャー追加 |
| スパン構造 | 平坦（LLM呼び出し単位） | 階層化（Agent/Workflow/Tool） |
| コード変更 | 不要 | 計装コードの追加が必要 |
| ユースケース | PoC、シンプルなLLMアプリ | 本番運用、複雑なAgentアプリ |

**参考ドキュメント**:
- Auto Instrumentation: https://docs.datadoghq.com/llm_observability/instrumentation/auto_instrumentation/
- SDK Instrumentation: https://docs.datadoghq.com/llm_observability/instrumentation/sdk/?tab=python

---

## スパンの種類

[LLM Observability Terms](https://docs.datadoghq.com/llm_observability/terms/) より：

| スパン種類 | 説明 | 使用例 |
|-----------|------|--------|
| **Agent** | 動的にタスクを決定・実行するエージェント | `TravelSupportAgent.process_message()` |
| **Workflow** | 複数のステップを含む処理フロー | 条件抽出、プラン生成 |
| **Tool** | 外部ツールやAPIの呼び出し | 交通検索、ホテル検索、規程チェック |
| **LLM** | LLMへの直接呼び出し | OpenAI API呼び出し（自動計装される） |
| **Task** | 汎用的なタスク | データ変換、バリデーション |

---

## SDK の使い方

### 方法1: デコレータ

```python
from ddtrace.llmobs.decorators import agent, workflow, tool

@agent(name="my-agent")
async def process_message(...):
    pass

@workflow(name="extract-conditions")
async def extract_conditions(...):
    pass

@tool(name="search-hotels")
def search_hotels(...):
    pass
```

### 方法2: コンテキストマネージャー

```python
from ddtrace.llmobs import LLMObs

async def process_message(...):
    with LLMObs.agent(name="my-agent") as span:
        # 処理
        pass
```

### 方法3: インラインメソッド

```python
from ddtrace.llmobs import LLMObs

span = LLMObs.agent(name="my-agent")
# 処理
LLMObs.annotate(span=span, input_data="...", output_data="...")
span.finish()
```

---

## 実装例：Before / After

### 対象ファイル: `backend/app/agents/travel_agent.py`

### Before（Auto Instrumentation のみ）

```python
class TravelSupportAgent:
    
    async def process_message(
        self,
        user_message: str,
        session_data: SessionData,
    ) -> Dict[str, Any]:
        """ユーザーメッセージを処理"""
        
        # エージェントを実行
        result = await self.agent_executor.ainvoke({
            "input": user_message,
            "chat_history": chat_history,
            "context": context,
            "conditions": conditions,
        })
        
        # 条件を更新
        updated_conditions = await self._update_conditions(
            user_message, 
            session_data.conditions
        )
        
        return {
            "response": result.get("output", ""),
            "plans": plans,
            "updated_conditions": updated_conditions,
        }
```

**問題点**: 
- 全体が1つの平坦なトレースになる
- Agent内部の処理フロー（ツール呼び出し等）が見えない

---

### After（SDK Instrumentation）

```python
from ddtrace.llmobs import LLMObs
from ddtrace.llmobs.decorators import agent, workflow, tool

class TravelSupportAgent:
    
    @agent(name="travel-support-agent", session_id=lambda self, _, sd: sd.session_id)
    async def process_message(
        self,
        user_message: str,
        session_data: SessionData,
    ) -> Dict[str, Any]:
        """ユーザーメッセージを処理"""
        
        # Workflow: エージェント実行
        with LLMObs.workflow(name="agent_execution") as agent_span:
            LLMObs.annotate(
                span=agent_span,
                input_data={"user_message": user_message},
            )
            result = await self.agent_executor.ainvoke({
                "input": user_message,
                "chat_history": chat_history,
                "context": context,
                "conditions": conditions,
            })
            LLMObs.annotate(
                span=agent_span,
                output_data={"response": result.get("output", "")},
            )
        
        # Workflow: 条件抽出
        with LLMObs.workflow(name="condition_extraction") as extract_span:
            updated_conditions = await self._update_conditions(
                user_message, 
                session_data.conditions
            )
            LLMObs.annotate(
                span=extract_span,
                output_data=updated_conditions.model_dump(),
            )
        
        return {
            "response": result.get("output", ""),
            "plans": plans,
            "updated_conditions": updated_conditions,
        }
```

**改善点**:
- `travel-support-agent` がルートスパン（Agent）
- `agent_execution`, `condition_extraction` がネストされたWorkflow
- 各ワークフローの入出力が記録される

---

### 対象ファイル: `backend/app/agents/tools/*.py`

### Before

```python
class TransportationSearchTool(BaseTool):
    name: str = "transportation_search"
    
    def _run(self, departure: str, destination: str, preferred_type: str = None) -> Dict:
        # 検索ロジック
        return {"found": True, "options": [...]}
```

### After

```python
from ddtrace.llmobs import LLMObs

class TransportationSearchTool(BaseTool):
    name: str = "transportation_search"
    
    def _run(self, departure: str, destination: str, preferred_type: str = None) -> Dict:
        with LLMObs.tool(name="transportation_search") as span:
            LLMObs.annotate(
                span=span,
                input_data={
                    "departure": departure,
                    "destination": destination,
                    "preferred_type": preferred_type,
                },
            )
            
            # 検索ロジック（既存コードそのまま）
            result = {"found": True, "options": [...]}
            
            LLMObs.annotate(
                span=span,
                output_data=result,
            )
            return result
```

---

## 期待されるトレース構造

```
Agent: travel-support-agent (5.2s)
├── Workflow: agent_execution (3.8s)
│   ├── Tool: policy_checker (0.1s)
│   ├── Tool: transportation_search (0.2s)
│   ├── Tool: hotel_search (0.2s)
│   └── LLM: OpenAI.createChatCompletion (2.5s)  ← 自動計装
├── Workflow: condition_extraction (1.2s)
│   └── LLM: OpenAI.createChatCompletion (1.0s)  ← 自動計装
└── Workflow: plan_generation (0.2s)
    ├── Tool: transportation_search
    ├── Tool: hotel_search
    └── Tool: plan_generator
```

---

## 実装チェックリスト

- [ ] `travel_agent.py`: `process_message` に `@agent` デコレータ追加
- [ ] `travel_agent.py`: 各処理ブロックを `LLMObs.workflow()` でラップ
- [ ] `travel_agent.py`: `generate_plans` に `@workflow` デコレータ追加
- [ ] `tools/policy_checker.py`: `_run` に `LLMObs.tool()` 追加
- [ ] `tools/transportation_search.py`: `_run` に `LLMObs.tool()` 追加
- [ ] `tools/hotel_search.py`: `_run` に `LLMObs.tool()` 追加
- [ ] `tools/plan_generator.py`: `_run` に `LLMObs.tool()` 追加

---

## 作業ログ

### 2024-12-02

**完了した作業:**

1. **`travel_agent.py` の計装**
   - `from ddtrace.llmobs import LLMObs` をインポート
   - `process_message()` メソッド:
     - `LLMObs.agent(name="travel-support-agent")` でAgentスパンを作成
     - `LLMObs.workflow(name="langchain_agent_execution")` でエージェント実行をラップ
     - `LLMObs.workflow(name="condition_extraction")` で条件抽出をラップ
     - 各スパンで `LLMObs.annotate()` を使用して入出力データを記録
   - `generate_plans()` メソッド:
     - `LLMObs.workflow(name="plan_generation")` で全体をラップ
     - `LLMObs.tool(name="transportation_search")` で交通検索をラップ
     - `LLMObs.tool(name="hotel_search")` でホテル検索をラップ
     - `LLMObs.tool(name="plan_generator")` でプラン生成をラップ

**期待されるトレース構造:**

```
Agent: travel-support-agent
├── Workflow: langchain_agent_execution
│   └── LLM: OpenAI.createChatCompletion (自動計装)
├── Workflow: condition_extraction
│   └── LLM: OpenAI.createChatCompletion (自動計装)
└── (generate_plansが呼ばれた場合)
    └── Workflow: plan_generation
        ├── Tool: transportation_search
        ├── Tool: hotel_search
        └── Tool: plan_generator
```

**次のステップ:**
- [ ] ローカルでテスト
- [ ] Datadog LLM Observabilityで階層構造を確認

