# Python vs TypeScript 計装比較

このドキュメントでは、Datadog LLM Observability の計装方法について、Python版とTypeScript版の違いを詳しく解説する。

---

## 1. 概要比較

| 項目 | Python | TypeScript |
|------|--------|------------|
| パッケージ | `ddtrace` | `dd-trace` |
| 初期化方法 | `ddtrace-run` コマンド or コード内 | コード内で `tracer.init()` |
| LLMObs アクセス | `from ddtrace.llmobs import LLMObs` | `tracer.llmobs` |
| スパン作成 | コンテキストマネージャー (`with`) | コールバック関数 (`trace()`) |
| アノテーション | `LLMObs.annotate(span, ...)` | `llmobs.annotate(span, ...)` |
| Agentless | `DD_LLMOBS_AGENTLESS_ENABLED=1` | 同じ |

---

## 2. 初期化の違い

### Python版

```python
# 方法1: ddtrace-run コマンド（推奨）
# Dockerfile
CMD ["ddtrace-run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# 方法2: コード内で初期化
from ddtrace import tracer
tracer.configure(
    service="my-service",
    env="dev",
)
```

**特徴:**
- `ddtrace-run` を使うと自動計装が有効になる
- LangChain, OpenAI, FastAPI などが自動でトレースされる
- コードの変更なしで基本的なトレースが取れる

### TypeScript版

```typescript
// src/tracer.ts（必ず最初にインポート）
import tracer from "dd-trace";

tracer.init({
  service: process.env.DD_SERVICE || "my-service",
  env: process.env.DD_ENV || "dev",
  version: "typescript-mastra-v1",
  logInjection: true,
});

// LLMObs インターフェースを取得
export const llmobs = tracer.llmobs;
```

```typescript
// src/index.ts（エントリーポイント）
import "./tracer";  // 最初にインポート！
import tracer, { llmobs } from "./tracer";
// ... 他のインポート
```

**特徴:**
- `tracer.init()` を**他のモジュールより先に**呼び出す必要がある
- ESM (`type: "module"`) の場合、インポート順序に注意
- 自動計装の対象は限定的（OpenAI など）

---

## 3. スパン作成方法の違い

### Python版: コンテキストマネージャー

```python
from ddtrace.llmobs import LLMObs

# Agent スパン
with LLMObs.agent(
    name="travel-support-agent",
    session_id=session_id,
) as agent_span:
    
    # 入力アノテーション
    LLMObs.annotate(
        span=agent_span,
        input_data={
            "user_message": user_message,
            "version": "python-langchain-v1",
        },
    )
    
    # 内部で Workflow スパン
    with LLMObs.workflow(name="agent_execution") as workflow_span:
        LLMObs.annotate(
            span=workflow_span,
            input_data={"available_tools": ["tool1", "tool2"]},
        )
        
        # 処理
        result = await agent_executor.ainvoke(...)
        
        LLMObs.annotate(
            span=workflow_span,
            output_data={"tools_called": ["tool1"]},
        )
    
    # 出力アノテーション
    LLMObs.annotate(
        span=agent_span,
        output_data={"response_length": len(result)},
    )
```

**特徴:**
- `with` 文でスコープが明確
- スパンは自動的に終了
- ネストは `with` のネストで表現

### TypeScript版: コールバック関数

```typescript
import { llmobs } from "./tracer";

// Agent スパン
const response = await llmobs.trace(
  {
    kind: "agent",
    name: "travel-support-agent",
    sessionId: sessionId,
    mlApp: "llm-salessupport",
  },
  async (agentSpan) => {
    // 入力アノテーション
    llmobs.annotate(agentSpan, {
      inputData: {
        user_message: message,
        version: "typescript-mastra-v1",
      },
    });

    // 内部で Workflow スパン
    const result = await llmobs.trace(
      {
        kind: "workflow",
        name: "agent_execution",
      },
      async (workflowSpan) => {
        llmobs.annotate(workflowSpan, {
          inputData: { available_tools: ["tool1", "tool2"] },
        });

        // 処理
        const agentResult = await travelAgent.generate(message);

        llmobs.annotate(workflowSpan, {
          outputData: { tools_called: ["tool1"] },
        });

        return agentResult;
      }
    );

    // 出力アノテーション
    llmobs.annotate(agentSpan, {
      outputData: { response_length: result.text.length },
    });

    return result;
  }
);
```

**特徴:**
- `llmobs.trace()` はコールバックの戻り値を返す
- スパンはコールバック終了時に自動終了
- ネストはコールバックのネストで表現
- `kind` でスパン種類を指定（`agent`, `workflow`, `tool`, `llm`, `task`）

---

## 4. スパン種類 (kind) の対応

| Python メソッド | TypeScript kind | 用途 |
|----------------|-----------------|------|
| `LLMObs.agent()` | `kind: "agent"` | エージェント全体 |
| `LLMObs.workflow()` | `kind: "workflow"` | 処理フロー |
| `LLMObs.tool()` | `kind: "tool"` | ツール呼び出し |
| `LLMObs.llm()` | `kind: "llm"` | LLM 呼び出し |
| `LLMObs.task()` | `kind: "task"` | 汎用タスク |
| `LLMObs.embedding()` | `kind: "embedding"` | 埋め込み生成 |
| `LLMObs.retrieval()` | `kind: "retrieval"` | 検索/取得 |

---

## 5. アノテーションの違い

### Python版

```python
LLMObs.annotate(
    span=span,
    input_data={"key": "value"},      # 入力
    output_data={"key": "value"},     # 出力
    metadata={"key": "value"},        # メタデータ
    tags={"key": "value"},            # タグ
)
```

### TypeScript版

```typescript
llmobs.annotate(span, {
  inputData: { key: "value" },        // 入力（camelCase）
  outputData: { key: "value" },       // 出力（camelCase）
  metadata: { key: "value" },         // メタデータ
  tags: { key: "value" },             // タグ
});
```

**違い:**
- Python は `snake_case`、TypeScript は `camelCase`
- 機能は同一

---

## 6. 自動計装の違い

### Python版 (ddtrace-run 使用時)

自動計装される主なライブラリ:
- ✅ LangChain（AgentExecutor, Tools, Chains）
- ✅ OpenAI
- ✅ FastAPI
- ✅ httpx, requests
- ✅ PostgreSQL (asyncpg, psycopg2)

```python
# LangChain の AgentExecutor を使うと自動的に:
# - Agent スパン
# - Tool スパン（各ツール呼び出し）
# - LLM スパン（OpenAI 呼び出し）
# が生成される
```

### TypeScript版

自動計装される主なライブラリ:
- ✅ OpenAI
- ⚠️ Mastra（自動計装なし → 手動で `llmobs.trace()` が必要）
- ⚠️ Hono（自動計装なし）

```typescript
// Mastra の Agent を使う場合、手動で計装が必要:
await llmobs.trace({ kind: "agent", name: "my-agent" }, async (span) => {
  const result = await mastraAgent.generate(...);
  return result;
});
```

---

## 7. デコレータ vs ラッパー

### Python版: デコレータ

```python
from ddtrace.llmobs.decorators import workflow, agent, tool

@agent(name="my-agent")
async def process_message(message: str):
    # 自動的に Agent スパンでラップされる
    return await do_something(message)

@workflow(name="my-workflow")
def my_workflow():
    pass

@tool(name="my-tool")
def my_tool():
    pass
```

### TypeScript版: wrap 関数

```typescript
// デコレータ風（クラスメソッド用）
class MyAgent {
  @llmobs.decorate({ kind: "agent" })
  async runChain() {
    // 自動的に Agent スパンでラップされる
  }
}

// 関数ラッパー
function processMessage() { ... }
processMessage = llmobs.wrap(
  { kind: "workflow", name: "processMessage" },
  processMessage
);
```

---

## 8. エラーハンドリング

### Python版

```python
with LLMObs.agent(name="my-agent") as span:
    try:
        result = await process()
    except Exception as e:
        # スパンは自動的にエラー状態になる
        LLMObs.annotate(
            span=span,
            metadata={"error": str(e)},
        )
        raise
```

### TypeScript版

```typescript
await llmobs.trace({ kind: "agent", name: "my-agent" }, async (span) => {
  try {
    return await process();
  } catch (error) {
    // スパンは自動的にエラー状態になる
    llmobs.annotate(span, {
      metadata: { error: error.message },
    });
    throw error;
  }
});
```

---

## 9. 環境変数（共通）

```bash
# 共通設定
DD_API_KEY=<your-api-key>
DD_ENV=dev
DD_LLMOBS_ENABLED=1
DD_LLMOBS_ML_APP=llm-salessupport
DD_LLMOBS_AGENTLESS_ENABLED=1

# サービス名（バックエンドごとに変更）
DD_SERVICE=llm-salessupport-backend-python
# または
DD_SERVICE=llm-salessupport-backend-typescript
```

---

## 10. まとめ

| 観点 | Python | TypeScript |
|------|--------|------------|
| **初期化** | `ddtrace-run` で簡単 | コードで `tracer.init()` |
| **構文** | `with` 文（コンテキストマネージャー） | コールバック関数 |
| **自動計装** | LangChain フル対応 | 限定的（手動計装推奨） |
| **学習コスト** | 低い | やや高い |
| **柔軟性** | 中 | 高い |

### 推奨

- **Python + LangChain**: `ddtrace-run` + 自動計装で十分
- **TypeScript + Mastra**: 手動で `llmobs.trace()` を使う

---

## 11. 導入時の変更パターン

既存コードに LLM Observability を導入する際に、**何を変更する必要があるか**を整理する。

---

### Python版: 変更の難易度「低」

#### ステップ1: 依存追加（追記のみ）

```diff
# requirements.txt
+ ddtrace>=3.11.0
```

#### ステップ2: 起動コマンド変更（1行変更）

```diff
# Dockerfile
- CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
+ CMD ["ddtrace-run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### ステップ3: カスタム計装（追記のみ）

既存の処理関数を **`with` 文で囲むだけ**。ロジックの変更は不要。

```diff
# 既存コード
  async def process_message(self, user_message: str, session_data: SessionData):
+     from ddtrace.llmobs import LLMObs
+     
+     with LLMObs.agent(name="travel-support-agent", session_id=session_data.session_id) as span:
+         LLMObs.annotate(span=span, input_data={"user_message": user_message})
+         
          # === 既存のロジックはそのまま ===
          result = await self.agent_executor.ainvoke({...})
          
+         LLMObs.annotate(span=span, output_data={"response": result})
+         
          return result
```

#### Python版まとめ

| 変更箇所 | 変更内容 | 難易度 |
|---------|---------|-------|
| `requirements.txt` | 1行追加 | ⭐ |
| `Dockerfile` | コマンド変更 | ⭐ |
| ビジネスロジック | `with`文で囲む（ロジック変更なし） | ⭐⭐ |
| **設計変更** | **不要** | - |

**結論: 既存コードを「囲む」だけ。設計変更は不要。**

---

### TypeScript版: 変更の難易度「中」

#### ステップ1: 依存追加（追記のみ）

```diff
# package.json
  "dependencies": {
+   "dd-trace": "^5.0.0",
    ...
  }
```

#### ステップ2: トレーサー初期化ファイル作成（新規ファイル）

```typescript
// src/tracer.ts（新規作成）
import tracer from "dd-trace";

tracer.init({
  service: process.env.DD_SERVICE,
  env: process.env.DD_ENV,
});

export const llmobs = tracer.llmobs;
export default tracer;
```

#### ステップ3: エントリーポイント変更（インポート順序が重要）

```diff
# src/index.ts
+ // トレーサーは最初にインポート（他のモジュールより前）
+ import "./tracer";
+ import { llmobs } from "./tracer";
+
  import { serve } from "@hono/node-server";
  import { Hono } from "hono";
  // ...
```

⚠️ **注意**: インポート順序を間違えると計装が効かない

#### ステップ4: カスタム計装（構造変更が必要）

既存の処理を **コールバック関数でラップ** する必要がある。
**戻り値の扱いが変わる**ため、若干のリファクタリングが必要。

```diff
# 既存コード（Before）
  chatRouter.post("/", async (c) => {
    const { message } = await c.req.json();
    
    // 直接処理
    const result = await travelAgent.generate(message);
    
    return c.json({ response: result.text });
  });
```

```diff
# 計装後（After）
  chatRouter.post("/", async (c) => {
    const { message } = await c.req.json();
    
+   // コールバック関数でラップ
+   const response = await llmobs.trace(
+     { kind: "agent", name: "travel-support-agent" },
+     async (span) => {
+       llmobs.annotate(span, { inputData: { message } });
+       
        const result = await travelAgent.generate(message);
        
+       llmobs.annotate(span, { outputData: { response: result.text } });
+       
+       return { response: result.text };  // 戻り値を返す
+     }
+   );
+   
+   return c.json(response);  // コールバックの戻り値を使う
-   return c.json({ response: result.text });
  });
```

#### TypeScript版まとめ

| 変更箇所 | 変更内容 | 難易度 |
|---------|---------|-------|
| `package.json` | 1行追加 | ⭐ |
| `src/tracer.ts` | 新規ファイル作成 | ⭐⭐ |
| `src/index.ts` | インポート順序変更 | ⭐⭐ |
| ビジネスロジック | **コールバックでラップ（戻り値の扱い変更）** | ⭐⭐⭐ |
| **設計変更** | **軽微なリファクタリングが必要** | - |

**結論: コールバック構造への変更が必要。戻り値の扱いが変わる。**

---

### 比較表

| 観点 | Python | TypeScript |
|------|--------|------------|
| **依存追加** | 1行 | 1行 |
| **新規ファイル** | 不要 | `tracer.ts` 必要 |
| **起動方法** | `ddtrace-run` 追加 | インポート順序変更 |
| **ロジック変更** | `with`で囲むだけ | コールバックでラップ |
| **戻り値の扱い** | 変更なし | **変更あり** |
| **設計変更** | 不要 | 軽微 |
| **総合難易度** | ⭐⭐ | ⭐⭐⭐ |

---

### なぜ TypeScript の方が難しいか

1. **コールバック構造**
   - Python: `with`文は既存コードを「囲む」だけ
   - TypeScript: コールバック内に処理を移動する必要がある

2. **戻り値の扱い**
   - Python: 既存の`return`はそのまま使える
   - TypeScript: コールバックから`return`し、その値を使う構造に変更

3. **初期化タイミング**
   - Python: `ddtrace-run`が自動で初期化
   - TypeScript: 手動で初期化、インポート順序に注意

4. **自動計装の範囲**
   - Python: LangChain が自動で計装される
   - TypeScript: Mastra は自動計装されない → 手動計装必須

---

## 12. 参考リンク

- [Datadog LLM Observability SDK (Python)](https://docs.datadoghq.com/llm_observability/instrumentation/sdk?tab=python)
- [Datadog LLM Observability SDK (Node.js)](https://docs.datadoghq.com/llm_observability/instrumentation/sdk?tab=nodejs)
- [ddtrace Python ドキュメント](https://ddtrace.readthedocs.io/)
- [dd-trace Node.js ドキュメント](https://datadoghq.dev/dd-trace-js/)

