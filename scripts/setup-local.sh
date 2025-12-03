#!/bin/bash

# ローカル開発環境セットアップスクリプト

set -e

echo "🚀 営業出張サポートAI - ローカル環境セットアップ"
echo ""

# 1. PostgreSQL起動
echo "📦 PostgreSQLを起動中..."
docker-compose -f docker-compose.dev.yml up -d

# 2. バックエンドセットアップ
echo ""
echo "🐍 バックエンドのセットアップ..."
cd backend

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt

# .envファイルがなければサンプルからコピー
if [ ! -f ".env" ]; then
    echo "⚠️  .envファイルが見つかりません。"
    echo "   backend/.env.example を参考に backend/.env を作成してください。"
    echo "   OPENAI_API_KEY の設定が必要です。"
fi

cd ..

# 3. フロントエンドセットアップ
echo ""
echo "⚛️  フロントエンドのセットアップ..."
cd frontend
npm install
cd ..

echo ""
echo "✅ セットアップ完了！"
echo ""
echo "📝 次のステップ:"
echo "   1. backend/.env を作成し、OPENAI_API_KEY を設定"
echo "   2. バックエンド起動: cd backend && source venv/bin/activate && uvicorn app.main:app --reload"
echo "   3. フロントエンド起動: cd frontend && npm run dev"
echo ""
echo "🌐 アクセス:"
echo "   - フロントエンド: http://localhost:5173"
echo "   - バックエンドAPI: http://localhost:8000"
echo "   - APIドキュメント: http://localhost:8000/docs"

