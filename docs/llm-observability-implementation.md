# LLM Observability 実装メモ

## 概要

このドキュメントでは、Datadog LLM Observability を本プロジェクトに導入した際の実装内容、学んだこと、設計判断をまとめる。

---

## 1. 実装したこと

### 1.1 ddtrace の導入

```bash
# requirements.txt に追加
ddtrace>=3.11.0
```

```dockerfile
# Dockerfile の CMD を変更
CMD ["ddtrace-run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 1.2 環境変数の設定

```bash
DD_API_KEY=<your-api-key>
DD_SERVICE=python-llm-salessupport-demo-backend
DD_ENV=dev
DD_LLMOBS_ENABLED=1
DD_LLMOBS_ML_APP=python-llm-salessupport-demo
DD_LLMOBS_AGENTLESS_ENABLED=1
```

### 1.3 AgentExecutor ベースへの変更

**変更前**: 4段階フロー（コードがツールを呼び分け）
```python
# コードが条件判断してツールを呼ぶ
if should_check_policy:
    policy_result = policy_tool._run(...)

if not is_day_trip:
    hotel_result = hotel_tool._run(...)
```

**変更後**: AgentExecutor（LLMがツールを選択）
```python
# LLMが自律的にツールを選択
result = await self.agent_executor.ainvoke({
    "input": user_message,
    ...
})
```

---

## 2. LangChain と ddtrace の連携

### 2.1 LangChain でのツール定義

```python
from langchain.tools import BaseTool

class PolicyCheckerTool(BaseTool):
    name: str = "policy_checker"
    description: str = "社内旅費規程をチェックします..."
    args_schema: type[BaseModel] = PolicyCheckInput
    
    def _run(self, ...):
        # 実際の処理
```

- `BaseTool` を継承 → LangChain が「ツール」と認識
- `name` と `description` → OpenAI の Function Calling に渡される
- `args_schema` → 引数のスキーマが自動生成される

### 2.2 ddtrace の自動検知

| LangChain クラス | ddtrace が認識するスパン種類 |
|-----------------|---------------------------|
| `BaseTool` | Tool スパン |
| `AgentExecutor` | Agent スパン |
| `ChatOpenAI` | LLM スパン |
| `BaseChain` | Chain スパン |

ddtrace は LangChain のこれらのクラスを **自動的に検知** してトレースを生成する。
特別なアノテーションは不要。

### 2.3 手動計装（オプション）

より詳細な階層構造が欲しい場合は、LLMObs SDK で手動追加：

```python
from ddtrace.llmobs import LLMObs

with LLMObs.agent(name="travel-support-agent", session_id=session_id) as span:
    with LLMObs.workflow(name="agent_execution") as exec_span:
        result = await self.agent_executor.ainvoke(...)
```

| デコレータ/コンテキスト | 用途 |
|----------------------|------|
| `LLMObs.agent()` | エージェント全体を囲む |
| `LLMObs.workflow()` | 処理フローのグループ化 |
| `LLMObs.tool()` | ツール呼び出し |
| `@LLMObs.llm()` | LLM 呼び出し |

---

## 3. Tool Selection Evaluation

### 3.1 機能

Datadog の Tool Selection Evaluation は：
- LLM が「正しいツールを選んだか」を評価
- LLM ベースの評価（別の LLM が判定）

### 3.2 動作条件

Tool Selection Evaluation が機能するには：

1. **LLM がツールを選択する形式であること**
   - AgentExecutor を使う
   - または OpenAI の Function Calling を直接使う

2. **コードがツールを呼び分ける形式では動作しない**
   ```python
   # ❌ これでは Tool Selection Evaluation が動かない
   if some_condition:
       tool._run(...)
   ```

### 3.3 設定

Datadog UI で Evaluation を作成：
- Application: `python-llm-salessupport-demo`
- Span Kind: `LLM`
- Span Names: `OpenAI.createChatCompletion`
- Tags: （オプション）

---

## 4. Agentless モードについて

### 4.1 なぜ Agentless で動くのか

通常、Datadog APM は Datadog Agent を経由してデータを送信する：

```
アプリ → Datadog Agent (localhost:8126) → Datadog
```

しかし、LLM Observability は **Agentless モード** をサポート：

```
アプリ → 直接 Datadog (llmobs-intake.datadoghq.com) → Datadog
```

### 4.2 設定

```bash
DD_LLMOBS_AGENTLESS_ENABLED=1
DD_API_KEY=<your-api-key>
```

### 4.3 Agentless が使える理由

1. **LLM Observability は独立したデータパス**
   - APM トレースとは別の intake エンドポイント
   - `llmobs-intake.datadoghq.com` に直接送信

2. **設計上の意図**
   - LLM アプリはサーバーレスや開発環境で動かすことが多い
   - Agent のセットアップなしで手軽に試せるように

### 4.4 注意点

| モード | LLM Obs | APM |
|--------|---------|-----|
| Agentless | ✅ 動く | ❌ 動かない |
| Agent あり | ✅ 動く | ✅ 動く |

現在のローカル環境では Agent がないため、APM トレースは送信されていない（エラーログに `failed to send traces` が出る）。

---

## 5. テストパターン

### 5.1 全ツール呼び出し

```bash
./scripts/test-prompts.sh all
```

メッセージ例：
```
東京から大阪に出張したいです。12月9日出発、12月10日帰着で、
新幹線を使いたいです。予算は5万円です。
この条件で社内規程に違反しないか確認して、プランを提案してください。
```

期待されるツール呼び出し：
- `policy_checker` ✓
- `transportation_search` ✓
- `hotel_search` ✓
- `plan_generator` ✓

### 5.2 一部スキップ（日帰り）

```bash
./scripts/test-prompts.sh skip
```

メッセージ例：
```
東京から名古屋に日帰りで出張したいです。12月15日に行って、当日中に戻ります。
```

期待されるツール呼び出し：
- `transportation_search` ✓
- `plan_generator` ✓
- `hotel_search` ✗ スキップ（日帰りのため）

---

## 6. アーキテクチャ図

```
┌─────────────────────────────────────────────────────────────────┐
│ Frontend (React)                                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ POST /api/chat
┌─────────────────────────────────────────────────────────────────┐
│ Backend (FastAPI + ddtrace)                                     │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ TravelSupportAgent                                        │ │
│  │                                                           │ │
│  │  ┌─────────────────────────────────────────────────────┐ │ │
│  │  │ AgentExecutor (LangChain)                           │ │ │
│  │  │                                                     │ │ │
│  │  │  LLM (GPT-4o) ──┬── policy_checker (Tool)          │ │ │
│  │  │                 ├── transportation_search (Tool)    │ │ │
│  │  │                 ├── hotel_search (Tool)             │ │ │
│  │  │                 └── plan_generator (Tool)           │ │ │
│  │  └─────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ddtrace 自動計装:                                              │
│    - LLM 呼び出しを検知 → LLM スパン                           │
│    - Tool 呼び出しを検知 → Tool スパン                          │
│    - Agent 実行を検知 → Agent スパン                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ Agentless 送信
┌─────────────────────────────────────────────────────────────────┐
│ Datadog LLM Observability                                       │
│                                                                 │
│  - Traces: LLM 呼び出しの階層構造                               │
│  - Evaluations: Tool Selection 評価                             │
│  - Metrics: トークン使用量、レイテンシ                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. 今後の課題

- [ ] ECS Fargate での Datadog Agent サイドカー設定（APM も有効化）
- [ ] Tool Selection Evaluation の結果確認・アラート設定
- [ ] Goal Completeness Evaluation の実装（セッション終了タグ）
- [ ] FireLens への切り替え
- [ ] Terraform での IaC 化

---

## 8. 参考リンク

- [Datadog LLM Observability ドキュメント](https://docs.datadoghq.com/llm_observability/)
- [Agent Evaluations](https://docs.datadoghq.com/llm_observability/evaluations/managed_evaluations/agent_evaluations/)
- [ddtrace Python SDK](https://docs.datadoghq.com/tracing/trace_collection/automatic_instrumentation/dd_libraries/python/)
- [LangChain Tools](https://python.langchain.com/docs/how_to/custom_tools/)


