# LLM Observability 実装ガイド

Datadog LLM Observability の実装方法をまとめたドキュメント。

---

## 1. アプリケーション概要

### 構成

| バックエンド | フレームワーク | バージョンタグ | ml_app |
|-------------|--------------|---------------|--------|
| Python | LangChain + FastAPI | `python-langchain-v1` | `python-llm-salessupport` |
| TypeScript | Mastra + Hono | `typescript-mastra-v1` | `typescript-llm-salessupport` |
| Python (Vertex AI) | Vertex AI (Gemini) + FastAPI | `python-vertex-v1` | `python-llm-salessupport-vertex` |

### ツール一覧

| ツール名 | 説明 |
|---------|------|
| `policy_checker` | 社内旅費規程をチェック |
| `transportation_search` | 交通手段を検索 |
| `hotel_search` | ホテルを検索 |
| `plan_generator` | 出張プランを生成（内部で transportation_search, hotel_search を呼び出す） |

### 処理フロー

```
ユーザー → travel-support-agent → LLM
                   ↓
         ツール選択（LLMが自律的に判断）
                   ↓
    ┌──────────────┼──────────────┐
    ↓              ↓              ↓
policy_checker  plan_generator  (直接レスポンス)
                   ↓
         ┌─────────┴─────────┐
         ↓                   ↓
transportation_search   hotel_search
```

**ポイント**: `plan_generator` は内部で他ツールを呼び出すため、トレースがネスト構造になる。

---

## 2. 環境変数

### Python版
```bash
DD_API_KEY=<your-api-key>
DD_SERVICE=python-llm-salessupport
DD_ENV=dev
DD_LLMOBS_ENABLED=1
DD_LLMOBS_ML_APP=python-llm-salessupport
DD_LLMOBS_AGENTLESS_ENABLED=1
```

### TypeScript版
```bash
DD_API_KEY=<your-api-key>
DD_SERVICE=typescript-llm-salessupport
DD_ENV=dev
DD_LLMOBS_ENABLED=1
DD_LLMOBS_ML_APP=typescript-llm-salessupport
DD_LLMOBS_AGENTLESS_ENABLED=1
```

### Vertex版（Python + Vertex AI）
```bash
DD_API_KEY=<your-api-key>
DD_SERVICE=kentomax-sales-support-backend-vertex
DD_ENV=dev
DD_LLMOBS_ENABLED=1
DD_LLMOBS_ML_APP=python-llm-salessupport-vertex
DD_LLMOBS_AGENTLESS_ENABLED=1
```

### Datadogで確認
```
https://app.datadoghq.com/llm/traces
フィルタ: 
  - Python版: ml_app:python-llm-salessupport
  - TypeScript版: ml_app:typescript-llm-salessupport
  - Vertex版: ml_app:python-llm-salessupport-vertex
```

---

## 3. 計装方式の比較

### 自動計装 vs 手動計装

| 項目 | 自動計装 | 手動計装 |
|------|---------|---------|
| 導入方法 | `ddtrace-run` / `tracer.init()` | デコレータ / コンテキストマネージャー |
| スパン構造 | 平坦（LangChain/OpenAI単位） | 階層化（Agent → Workflow → Tool） |
| コード変更 | 不要 | 計装コードの追加が必要 |
| 対応範囲 | Python: LangChain, OpenAI / TS: 限定的 | 任意の処理 |

### 本プロジェクトでの方針

| 処理 | Python (LangChain) | TypeScript (Mastra) | Python (Vertex AI) |
|------|------------------|-------------------|-------------------|
| LangChain/OpenAI呼び出し | **自動計装** | N/A | N/A |
| Vertex AI SDK 呼び出し | N/A | N/A | **自動計装**（ddtrace + Vertex AI integration） |
| Agent全体 | **手動計装**（LLMObs.agent） | **手動計装**（llmobs.trace kind=agent） | なし（現状） |
| Workflow | **手動計装**（LLMObs.workflow） | **手動計装**（llmobs.trace kind=workflow） | なし（現状） |
| Tool | **手動計装**（@llmobs_tool） | **手動計装**（llmobs.trace kind=tool） | なし（現状） |
| LLM呼び出し | **自動計装**（LangChain/OpenAI） | **手動計装**（llmobs.trace kind=llm） | **自動計装**（Vertex AI SDK） |

**補足（Vertex版）**: Vertex版は「まず auto instrumentation のみ」で導入しています。Python/LangChain版のように階層スパン（Agent/Workflow/Tool）を作りたい場合は、`backend-python-vertex` 側に `LLMObs.agent/workflow` 等の手動計装を追加していく方針になります。

---

## 4. Python版実装

### 4.1 初期化

```python
# backend-python/app/main.py
import os
from ddtrace.llmobs import LLMObs

if os.getenv("DD_LLMOBS_ENABLED") == "1":
    # LLMObs 明示的初期化（agentless の場合は DD_API_KEY が必要）
    LLMObs.enable(
        ml_app=os.getenv("DD_LLMOBS_ML_APP", "python-llm-salessupport"),
        agentless_enabled=os.getenv("DD_LLMOBS_AGENTLESS_ENABLED") == "1",
    )
```

### 4.2 Tool計装（デコレータ）

```python
# app/agents/tools/hotel_search.py
from ddtrace.llmobs.decorators import tool as llmobs_tool

class HotelSearchTool(BaseTool):
    name: str = "hotel_search"
    
    @llmobs_tool(name="hotel_search")
    def _run(self, destination: str, nights: int = 1, ...) -> Dict[str, Any]:
        # 処理
        return result
```

### 4.3 Agent/Workflow計装（コンテキストマネージャー）

```python
# app/agents/travel_agent.py
from ddtrace.llmobs import LLMObs

async def process_message(self, user_message: str, session_data: SessionData):
    # Agent スパン
    with LLMObs.agent(
        name="travel-support-agent",
        session_id=session_data.session_id,
    ) as agent_span:
        LLMObs.annotate(
            span=agent_span,
            input_data={"user_message": user_message, "version": APP_VERSION},
        )
        
        # Workflow スパン
        with LLMObs.workflow(name="agent_execution") as workflow_span:
            result = await self.agent_executor.ainvoke({...})
        
        LLMObs.annotate(span=agent_span, output_data={"response": result})
        return result
```

---

## 5. TypeScript版実装

### 5.1 初期化（tracer.ts）

```typescript
// dotenvを最初にインポート
import "dotenv/config";
import tracer from "dd-trace";

tracer.init({
  service: process.env.DD_SERVICE || "llm-salessupport",
  env: process.env.DD_ENV || "dev",
  version: "typescript-mastra-v1",
  llmobs: {
    mlApp: process.env.DD_LLMOBS_ML_APP || "llm-salessupport",
    agentlessEnabled: process.env.DD_LLMOBS_AGENTLESS_ENABLED === "1",
    apiKey: process.env.DD_API_KEY,
  },
});

export const llmobs = tracer.llmobs;
```

**重要**: `dotenv/config` は `tracer.ts` より先にインポートする

```typescript
// src/index.ts
import "dotenv/config";  // 最初
import "./tracer";        // 次
// ... 他のインポート
```

### 5.2 Tool計装（llmobs.trace）

```typescript
// src/tools/hotelSearch.ts
export const hotelSearchTool = createTool({
  id: "hotel_search",
  execute: async ({ context }) => {
    return await llmobs.trace(
      { kind: "tool", name: "hotel_search" },
      async (toolSpan) => {
        llmobs.annotate(toolSpan, {
          inputData: { destination: context.destination, ... },
        });
        
        const result = { hotels: [...], search_summary: "..." };
        
        llmobs.annotate(toolSpan, {
          outputData: { hotels_count: result.hotels.length },
        });
        return result;
      }
    );
  },
});
```

### 5.3 Agent/Workflow/LLM計装

```typescript
// src/routes/chat.ts
const response = await llmobs.trace(
  { kind: "agent", name: "travel-support-agent", sessionId, mlApp },
  async (agentSpan) => {
    llmobs.annotate(agentSpan, { inputData: { user_message: message } });
    
    const result = await llmobs.trace(
      { kind: "workflow", name: "agent_execution" },
      async (workflowSpan) => {
        // LLMスパン（Mastra/Vercel AI SDKは自動計装されないため手動）
        return await llmobs.trace(
          { kind: "llm", name: "openai.chat", modelName: "gpt-4o", modelProvider: "openai" },
          async (llmSpan) => {
            const agentResult = await travelAgent.generate(message);
            llmobs.annotate(llmSpan, { outputData: { content: agentResult.text } });
            return agentResult;
          }
        );
      }
    );
    
    llmobs.annotate(agentSpan, { outputData: { response_length: result.text.length } });
    return result;
  }
);
```

### 5.4 plan_generatorのネスト構造

`plan_generator` は内部で他ツールを呼び出すため、ネストしたToolスパンを作成：

```typescript
// src/tools/planGenerator.ts
execute: async ({ context }) => {
  return await llmobs.trace(
    { kind: "tool", name: "plan_generator" },
    async (toolSpan) => {
      // 内部でtransportation_searchを呼び出し
      const transportationOptions = await llmobs.trace(
        { kind: "tool", name: "transportation_search" },
        async (transSpan) => {
          return searchTransportation(...);
        }
      );
      
      // 内部でhotel_searchを呼び出し
      const hotelOptions = await llmobs.trace(
        { kind: "tool", name: "hotel_search" },
        async (hotelSpan) => {
          return searchHotels(...);
        }
      );
      
      // プラン生成
      return { plans: [...] };
    }
  );
},
```

---

## 6. スパン種類（kind）

| kind | 用途 | 例 |
|------|------|-----|
| `agent` | エージェント全体 | `travel-support-agent` |
| `workflow` | 処理フロー | `agent_execution` |
| `tool` | ツール呼び出し | `hotel_search`, `plan_generator` |
| `llm` | LLM API呼び出し | `openai.chat` |
| `task` | 汎用タスク | データ変換 |
| `embedding` | 埋め込み生成 | ベクトル化 |
| `retrieval` | 検索/取得 | RAG |

---

## 7. 期待されるトレース構造

### Python版（自動計装 + 手動計装）

```
Agent: travel-support-agent (10.7s)
├── Workflow: agent_execution (9.4s)
│   ├── langchain_core.runnables... (3.4s)
│   │   └── OpenAI.createChatCompletion (3.4s)  ← 自動計装
│   ├── Tool: plan_generator (0.8s)
│   │   ├── Tool: transportation_search (0.1s)
│   │   └── Tool: hotel_search (0.2s)
│   ├── Tool: policy_checker (0.1s)
│   └── langchain_core.runnables... (6.2s)
│       └── OpenAI.createChatCompletion (6.2s)  ← 自動計装
```

### TypeScript版（手動計装）

```
Agent: travel-support-agent (8.5s)
├── Workflow: agent_execution (8.5s)
│   └── LLM: openai.chat (7.6s)  ← 手動計装
│       ├── Tool: policy_checker (0.3s)
│       ├── Tool: hotel_search (0.4s)
│       ├── Tool: transportation_search (1.1s)
│       └── Tool: plan_generator (0.5s)
│           ├── Tool: transportation_search (0.1s)  ← ネスト
│           └── Tool: hotel_search (0.1s)           ← ネスト
```

---

## 8. Python vs TypeScript 比較

| 観点 | Python | TypeScript |
|------|--------|------------|
| **初期化** | `ddtrace-run` or `LLMObs.enable()` | `tracer.init()` |
| **構文** | `with` 文（コンテキストマネージャー） | コールバック関数 |
| **自動計装** | LangChain/OpenAI フル対応 | 限定的（手動計装推奨） |
| **Toolデコレータ** | `@llmobs_tool(name="...")` | なし（`llmobs.trace()`使用） |
| **命名規則** | `snake_case` | `camelCase` |
| **学習コスト** | 低い | やや高い |

---

## 9. カスタムタグ機能

会社名やユーザーIDなどのカスタムタグをスパンに付与し、Datadogでフィルタリング・集計が可能。

### 9.1 実装方法（Python版）

`LLMObs.annotate()` の `tags` パラメータを使用：

```python
# app/agents/travel_agent.py
with LLMObs.agent(name="travel-support-agent", session_id=session_id) as agent_span:
    # カスタムタグを追加
    custom_tags = {
        "company_name": company_name,  # 会社名
        "user_id": user_id,            # ユーザーID
    }
    
    LLMObs.annotate(
        span=agent_span,
        input_data={...},
        tags=custom_tags,  # ← タグを追加
    )
```

### 9.2 APIリクエスト

`company_name` フィールドをリクエストに含める：

```json
{
    "message": "東京から大阪に出張したい",
    "user_id": "test-user",
    "company_name": "A株式会社"
}
```

### 9.3 Datadogでのフィルタリング

```
@tags.company_name:"A株式会社"
@tags.user_id:"test-user"
```

### 9.4 テストスクリプト

```bash
./scripts/test-company-tags.sh
```

複数の会社名でトレースを生成し、Datadogでフィルタリングをテスト。

---

## 10. 参考リンク

- [LLM Observability SDK (Python)](https://docs.datadoghq.com/llm_observability/instrumentation/sdk?tab=python)
- [LLM Observability SDK (Node.js)](https://docs.datadoghq.com/llm_observability/instrumentation/sdk?tab=nodejs)
- [Auto Instrumentation](https://docs.datadoghq.com/llm_observability/instrumentation/auto_instrumentation)
- [LLM Observability Terms](https://docs.datadoghq.com/llm_observability/terms/)

