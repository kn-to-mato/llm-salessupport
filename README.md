# 営業出張サポートAI デモアプリ

営業担当者の出張計画をAIがサポートするデモアプリケーションです。
LangChainを使用したAIエージェントが、社内旅費規程を参照しながら、最適な出張プランを提案します。

## 主な機能

- 🤖 **AIによる対話型出張計画**: 自然言語で出張の希望を伝えると、AIが条件を整理
- 📋 **社内旅費規程の自動チェック**: モック規程に基づいた予算・条件の確認
- 🚄 **交通手段の提案**: 新幹線・飛行機などの候補を自動検索
- 🏨 **宿泊先の提案**: 条件に合ったホテル候補を提示
- 📝 **申請データの自動生成**: 選択したプランから申請用データを生成

## 技術スタック

### バックエンド
- Python 3.11+
- FastAPI
- LangChain
- PostgreSQL
- OpenAI API (GPT-4.1)

### フロントエンド
- React 18
- TypeScript
- Vite
- Tailwind CSS

## セットアップ

### 前提条件

- Docker & Docker Compose
- Node.js 20+
- Python 3.11+
- OpenAI API キー

### 環境変数の設定

```bash
# バックエンド
cp backend/.env.example backend/.env
# OpenAI APIキーを設定してください

# フロントエンド
cp frontend/.env.example frontend/.env
```

### ローカル開発環境の起動

```bash
# Docker Composeで全サービスを起動
docker-compose up -d

# または個別に起動

# バックエンド
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# フロントエンド
cd frontend
npm install
npm run dev
```

### アクセス

- フロントエンド: http://localhost:5173
- バックエンドAPI: http://localhost:8000
- API ドキュメント: http://localhost:8000/docs

## API エンドポイント

### チャット送信
```
POST /api/chat
```

### プラン確定
```
POST /api/plan/confirm
```

詳細は [API ドキュメント](http://localhost:8000/docs) を参照してください。

## AWS デプロイ

本番環境は AWS ECS (Fargate) にデプロイされています。

### アクセスURL
```
http://kentomax-sales-support-alb-733711893.ap-northeast-1.elb.amazonaws.com
```

### 主要リソース
| リソース | 名前 |
|---------|------|
| ECSクラスター | `kentomax_sales-support-cluster` |
| ALB | `kentomax-sales-support-alb` |
| ECR (Backend) | `kentomax/sales-support/backend` |
| ECR (Frontend) | `kentomax/sales-support/frontend` |

詳細は [docs/aws-infrastructure.md](docs/aws-infrastructure.md) を参照してください。

### デプロイ手順（概要）

```bash
# AWS SSO ログイン
aws sso login --profile kentomax-admin

# イメージビルド & プッシュ
./scripts/build-and-push.sh

# ECSサービス更新
aws ecs update-service --cluster kentomax_sales-support-cluster --service kentomax_sales-support-backend --force-new-deployment --profile kentomax-admin --region ap-northeast-1
aws ecs update-service --cluster kentomax_sales-support-cluster --service kentomax_sales-support-frontend --force-new-deployment --profile kentomax-admin --region ap-northeast-1
```

## ライセンス

MIT License



