#!/bin/bash

# ECRへのビルド＆プッシュスクリプト
# 使用前に: aws sso login --profile kentomax-admin

set -e

PROFILE="kentomax-admin"
REGION="ap-northeast-1"
ACCOUNT_ID=$(aws sts get-caller-identity --profile $PROFILE --query Account --output text)
ECR_BASE="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

# ECRリポジトリ名
BACKEND_REPO="kentomax/sales-support/backend"
FRONTEND_REPO="kentomax/sales-support/frontend"

echo "🔐 ECRにログイン中..."
aws ecr get-login-password --region $REGION --profile $PROFILE | docker login --username AWS --password-stdin $ECR_BASE

echo ""
echo "🏗️ バックエンドイメージをビルド中..."
docker build --platform linux/amd64 -t $BACKEND_REPO:latest ./backend
docker tag $BACKEND_REPO:latest $ECR_BASE/$BACKEND_REPO:latest

echo ""
echo "🏗️ フロントエンドイメージをビルド中..."
docker build --platform linux/amd64 -t $FRONTEND_REPO:latest ./frontend
docker tag $FRONTEND_REPO:latest $ECR_BASE/$FRONTEND_REPO:latest

echo ""
echo "📤 ECRにプッシュ中..."

# リポジトリが存在しない場合は作成
aws ecr describe-repositories --repository-names $BACKEND_REPO --profile $PROFILE --region $REGION 2>/dev/null || \
    aws ecr create-repository --repository-name $BACKEND_REPO --profile $PROFILE --region $REGION \
    --tags Key=please_keep_it,Value=true Key=user,Value=kento.tomatsu

aws ecr describe-repositories --repository-names $FRONTEND_REPO --profile $PROFILE --region $REGION 2>/dev/null || \
    aws ecr create-repository --repository-name $FRONTEND_REPO --profile $PROFILE --region $REGION \
    --tags Key=please_keep_it,Value=true Key=user,Value=kento.tomatsu

docker push $ECR_BASE/$BACKEND_REPO:latest
docker push $ECR_BASE/$FRONTEND_REPO:latest

echo ""
echo "✅ 完了！"
echo ""
echo "イメージ:"
echo "  - Backend: $ECR_BASE/$BACKEND_REPO:latest"
echo "  - Frontend: $ECR_BASE/$FRONTEND_REPO:latest"
