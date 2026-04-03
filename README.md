# 営業出張サポートAI デモアプリ

営業担当者の出張計画をAIがサポートするデモアプリケーションです。
同じ機能を **Python + LangChain** と **TypeScript + Mastra** の2つの技術スタックで実装しています。
加えて、**Python + Vertex AI (Gemini)** のバックエンド（`backend-python-vertex/`）も追加しています。

## 🎯 主な機能

- 🤖 **AIによる対話型出張計画**: 自然言語で出張の希望を伝えると、AIが条件を整理
- 📋 **社内旅費規程の自動チェック**: モック規程に基づいた予算・条件の確認
- 🚄 **交通手段の提案**: 新幹線・飛行機などの候補を自動検索
- 🏨 **宿泊先の提案**: 条件に合ったホテル候補を提示
- 📝 **申請データの自動生成**: 選択したプランから申請用データを生成

## 📁 プロジェクト構成

```
llm-salessupport/
├── frontend/              # React フロントエンド（共通）
├── backend-python/        # Python + LangChain バックエンド
├── backend-python-vertex/  # Python + Vertex AI (Gemini) バックエンド
├── backend-typescript/    # TypeScript + Mastra バックエンド
├── docs/                  # ドキュメント
└── scripts/               # ユーティリティスクリプト
```

## 🛠️ 技術スタック

### フロントエンド（共通）
- React 18 + TypeScript
- Vite
- Tailwind CSS

### バックエンド（Python版）
| 技術 | 用途 |
|------|------|
| Python 3.11+ | 言語 |
| FastAPI | Webフレームワーク |
| LangChain | AIエージェント |
| ddtrace | Datadog LLM Observability |

### バックエンド（TypeScript版）
| 技術 | 用途 |
|------|------|
| TypeScript | 言語 |
| Hono | Webフレームワーク |
| Mastra | AIエージェント |

## 🚀 クイックスタート

### 前提条件
- Node.js 20+
- Python 3.11+
- OpenAI API キー

### 1. Python バックエンドで起動

```bash
# バックエンド起動
cd backend-python
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
OPENAI_API_KEY=sk-xxx uvicorn app.main:app --reload --port 8000

# フロントエンド起動（別ターミナル）
cd frontend
npm install
npm run dev
```

→ http://localhost:5173 にアクセス

### 2. TypeScript バックエンドで起動

```bash
# バックエンド起動
cd backend-typescript
npm install
OPENAI_API_KEY=sk-xxx npm run dev

# フロントエンド起動（別ターミナル）
cd frontend
npm install
VITE_BACKEND=typescript npm run dev
```

→ http://localhost:5174 にアクセス（`VITE_PORT` 未指定時のデフォルト）

## 🔀 バックエンド切り替え

フロントエンドは環境変数でバックエンドを切り替えできます：

```bash
# Python バックエンド（デフォルト）
npm run dev

# TypeScript バックエンド
VITE_BACKEND=typescript npm run dev

# カスタムURL指定
VITE_BACKEND_URL=http://localhost:9000 npm run dev
```

画面右上にバックエンドの種類がバッジで表示されます。

## 🌐 フロントを2つ同時に開く（ポートを分ける）

同じ `frontend/` を **2つ同時に起動**して、LangChain / Vertex AI をブラウザで並べて確認できます。

例（LangChain = 5173、Vertex = 5174）:

```bash
cd frontend

# ターミナルA（LangChain）
VITE_PORT=5173 VITE_BACKEND_URL=http://kentomax-sales-support-alb-733711893.ap-northeast-1.elb.amazonaws.com npm run dev

# ターミナルB（Vertex / Cloud Run）
VITE_PORT=5174 VITE_BACKEND_URL=https://kentomax-sales-support-backend-vertex-n4ow3sy4fq-an.a.run.app npm run dev
```

またはスクリプトで一括起動:

```bash
./scripts/run-dual-frontend.sh \
  --langchain-url http://kentomax-sales-support-alb-733711893.ap-northeast-1.elb.amazonaws.com \
  --vertex-url https://kentomax-sales-support-backend-vertex-n4ow3sy4fq-an.a.run.app
```

## 📊 Datadog LLM Observability

Python版・TypeScript版・Vertex版ともに Datadog LLM Observability に対応しています。

| バックエンド | ml_app名 | 対応状況 |
|-------------|---------|---------|
| Python | `python-llm-salessupport` | ✅ 自動計装 + 手動計装 |
| TypeScript | `typescript-llm-salessupport` | ✅ 手動計装 |
| Python (Vertex AI) | `python-llm-salessupport-vertex` | ✅ 自動計装（ddtrace-run, Vertex AI SDK） / ⏳ 手動計装は未（現状） |

```bash
# Python版
DD_API_KEY=xxx \
DD_SERVICE=python-llm-salessupport \
DD_ENV=dev \
DD_LLMOBS_ENABLED=1 \
DD_LLMOBS_ML_APP=python-llm-salessupport \
DD_LLMOBS_AGENTLESS_ENABLED=1 \
ddtrace-run uvicorn app.main:app --reload --port 8000
```

Vertex版（Cloud Run + Secret Manager）の詳細は [docs/gcp-infrastructure.md](docs/gcp-infrastructure.md) を参照。
詳細は [docs/llm-observability.md](docs/llm-observability.md) も参照。

### Hallucination Detection デモ運用メモ（2026-04）

- 今回の Hallucination トレース向け改修は **`backend-python/` のみ** に適用。
- `backend-python/app/agents/travel_agent.py` で、通常チャット処理中の `agent_executor.ainvoke(...)` を `LLMObs.annotation_context(prompt=...)` で包み、Datadog Evaluation が必要とする query/context を常時付与。
- このとき専用スパン名や入力プレフィックス（例: `[EVAL][HALLUCINATION]`）には依存しない。
- **`backend-typescript/` と `backend-python-vertex/` には同等の Hallucination 用手動注釈は未追加**（既存の実装方針のまま）。
- `scripts/comprehensive-test.sh` には Hallucination 検証入力（テスト9）を追加済み。入力は自然文だが、矛盾・未根拠主張を誘発しやすい内容にしている。

## 🐳 Docker Compose

```bash
# 全サービス起動
docker-compose up -d

# Python バックエンドのみ
docker-compose up -d db backend-python frontend

# TypeScript バックエンドのみ
docker-compose up -d backend-typescript
```

## 📝 API エンドポイント

両バックエンドとも同じAPIインターフェースを提供：

| エンドポイント | 説明 |
|---------------|------|
| `GET /health` | ヘルスチェック |
| `POST /api/chat` | チャット送信 |
| `POST /api/chat/reset` | セッションリセット |

## 🧪 テスト

```bash
# テストプロンプト実行
./scripts/test-prompts.sh
```

包括テスト（LangChain(AWS) と Vertex(Cloud Run) をまとめて）:

```bash
./scripts/comprehensive-test.sh dual \
  http://kentomax-sales-support-alb-733711893.ap-northeast-1.elb.amazonaws.com \
  https://kentomax-sales-support-backend-vertex-n4ow3sy4fq-an.a.run.app
```

`scripts/` の役割一覧は `scripts/README.md` を参照。

## 📚 ドキュメント

- [アプリケーションロジック仕様](docs/application-logic.md)
- [LLM Observability 実装ガイド](docs/llm-observability.md)
- [AWS インフラ構成](docs/aws-infrastructure.md)
- [Datadog APM 導入ガイド](docs/datadog-integration.md)
- [GCP インフラ構成（Cloud Run + Vertex AI）](docs/gcp-infrastructure.md)

## ライセンス

MIT License
