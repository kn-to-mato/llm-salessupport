# 営業出張サポートAI デモアプリ

営業担当者の出張計画をAIがサポートするデモアプリケーションです。
同じ機能を **Python + LangChain** と **TypeScript + Mastra** の2つの技術スタックで実装しています。

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

→ http://localhost:5173 にアクセス

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

## 📊 Datadog LLM Observability

Python版・TypeScript版ともに Datadog LLM Observability に対応しています。

| バックエンド | ml_app名 | 対応状況 |
|-------------|---------|---------|
| Python | `python-llm-salessupport` | ✅ 自動計装 + 手動計装 |
| TypeScript | `typescript-llm-salessupport` | ✅ 手動計装 |

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

詳細は [docs/llm-observability.md](docs/llm-observability.md) を参照。

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

## 📚 ドキュメント

- [アプリケーションロジック仕様](docs/application-logic.md)
- [LLM Observability 実装ガイド](docs/llm-observability.md)
- [AWS インフラ構成](docs/aws-infrastructure.md)
- [Datadog APM 導入ガイド](docs/datadog-integration.md)

## ライセンス

MIT License
