# AWS インフラストラクチャ構成

営業出張サポートAIデモアプリのAWSデプロイ情報

## アクセスURL

```
http://kentomax-sales-support-alb-733711893.ap-northeast-1.elb.amazonaws.com
```

## リソース一覧

### ネットワーク

| リソース | ID/名前 | 説明 |
|---------|--------|------|
| VPC | `vpc-01009428b03126ad9` (kentomax-vpc) | CIDR: 10.0.0.0/16 |
| Public Subnet 1 | `subnet-06cad38fdd89cbc4c` | ap-northeast-1a |
| Public Subnet 2 | `subnet-0a26bee435b639c7d` | ap-northeast-1c |
| Private Subnet 1 | `subnet-0fd4b03526b5ff4e0` | ap-northeast-1a |
| Private Subnet 2 | `subnet-0742f8bc3654c1155` | ap-northeast-1c |

### セキュリティグループ

| 名前 | ID | 用途 |
|-----|-----|------|
| kentomax_sales-support-alb-sg | `sg-0df9761f47921aa7f` | ALB用。HTTPアクセス許可 |
| kentomax_sales-support-ecs-sg | `sg-0c1eaf860431be681` | ECSタスク用。ALBからのみアクセス可 |

**セキュリティルール:**
- ALB SG: ポート80を特定IP (209.249.214.170/32) からのみ許可
- ECS SG: ALB SGからポート80, 8000を許可

### ECS

| リソース | 名前 | 説明 |
|---------|------|------|
| クラスター | `kentomax_sales-support-cluster` | 専用クラスター |
| サービス (Backend) | `kentomax_sales-support-backend` | FastAPI + LangChain |
| サービス (Frontend) | `kentomax_sales-support-frontend` | React + Nginx |
| タスク定義 (Backend) | `kentomax_sales-support-backend:1` | CPU: 512, Memory: 1024 |
| タスク定義 (Frontend) | `kentomax_sales-support-frontend:1` | CPU: 256, Memory: 512 |

### ECR

| リポジトリ | URI |
|-----------|-----|
| Backend | `369042512949.dkr.ecr.ap-northeast-1.amazonaws.com/kentomax/sales-support/backend` |
| Frontend | `369042512949.dkr.ecr.ap-northeast-1.amazonaws.com/kentomax/sales-support/frontend` |

### ALB

| リソース | 値 |
|---------|-----|
| 名前 | `kentomax-sales-support-alb` |
| ARN | `arn:aws:elasticloadbalancing:ap-northeast-1:369042512949:loadbalancer/app/kentomax-sales-support-alb/ce0f54fda6294cdb` |
| DNS | `kentomax-sales-support-alb-733711893.ap-northeast-1.elb.amazonaws.com` |
| リスナー | HTTP:80 |

**ターゲットグループ:**

| 名前 | ポート | パスルール |
|-----|-------|-----------|
| kentomax-sales-backend-tg | 8000 | `/api/*`, `/health` |
| kentomax-sales-frontend-tg | 80 | デフォルト (その他すべて) |

### Secrets Manager

| シークレット名 | 内容 |
|--------------|------|
| `kentomax_sales-support-secrets` | OPENAI_API_KEY, DB_PASSWORD |

### CloudWatch Logs

| ロググループ | 用途 |
|------------|------|
| `/ecs/kentomax_sales-support-backend` | バックエンドログ |
| `/ecs/kentomax_sales-support-frontend` | フロントエンドログ |

## アーキテクチャ図

```
                    ┌─────────────────┐
                    │   Internet      │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  ALB (HTTP:80)  │
                    │  kentomax-      │
                    │  sales-support  │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
     /api/*, /health                    その他
              │                             │
    ┌─────────▼─────────┐       ┌──────────▼──────────┐
    │  Backend (8000)   │       │  Frontend (80)      │
    │  FastAPI          │       │  Nginx + React      │
    │  LangChain        │       │                     │
    └───────────────────┘       └─────────────────────┘
              │
    ┌─────────▼─────────┐
    │  OpenAI API       │
    │  (外部)           │
    └───────────────────┘
```

## デプロイ手順

### 1. ECRへのイメージプッシュ

```bash
# AWS SSO ログイン
aws sso login --profile kentomax-admin

# ECRログイン
aws ecr get-login-password --region ap-northeast-1 --profile kentomax-admin | \
  docker login --username AWS --password-stdin 369042512949.dkr.ecr.ap-northeast-1.amazonaws.com

# バックエンドビルド&プッシュ
docker build --platform linux/amd64 -t kentomax/sales-support/backend:latest ./backend
docker tag kentomax/sales-support/backend:latest 369042512949.dkr.ecr.ap-northeast-1.amazonaws.com/kentomax/sales-support/backend:latest
docker push 369042512949.dkr.ecr.ap-northeast-1.amazonaws.com/kentomax/sales-support/backend:latest

# フロントエンドビルド&プッシュ
docker build --platform linux/amd64 -t kentomax/sales-support/frontend:latest ./frontend
docker tag kentomax/sales-support/frontend:latest 369042512949.dkr.ecr.ap-northeast-1.amazonaws.com/kentomax/sales-support/frontend:latest
docker push 369042512949.dkr.ecr.ap-northeast-1.amazonaws.com/kentomax/sales-support/frontend:latest
```

### 2. ECSサービスの更新

```bash
# バックエンド再デプロイ
aws ecs update-service \
  --cluster kentomax_sales-support-cluster \
  --service kentomax_sales-support-backend \
  --force-new-deployment \
  --profile kentomax-admin \
  --region ap-northeast-1

# フロントエンド再デプロイ
aws ecs update-service \
  --cluster kentomax_sales-support-cluster \
  --service kentomax_sales-support-frontend \
  --force-new-deployment \
  --profile kentomax-admin \
  --region ap-northeast-1
```

### 3. 状態確認

```bash
# サービス状態
aws ecs describe-services \
  --cluster kentomax_sales-support-cluster \
  --services kentomax_sales-support-backend kentomax_sales-support-frontend \
  --profile kentomax-admin \
  --region ap-northeast-1 \
  --query 'services[*].{Name:serviceName,Running:runningCount,Desired:desiredCount}'

# ログ確認
aws logs tail /ecs/kentomax_sales-support-backend --follow --profile kentomax-admin --region ap-northeast-1
```

## タグ規則

すべてのリソースに以下のタグを付与:

| キー | 値 |
|-----|-----|
| `please_keep_it` | `true` |
| `user` | `kento.tomatsu` |

## 注意事項

1. **セキュリティグループ**: ALBへのアクセスは特定IPのみ許可。変更時は `/32` で指定
2. **データ永続化なし**: 現在はインメモリセッション管理。ECS再起動でセッションリセット
3. **Aurora PostgreSQL**: `kentomax-eks-go-shop-aurora` が存在するが未接続（パスワード不明）

## 将来の拡張

- [ ] Aurora PostgreSQL接続によるセッション永続化
- [ ] HTTPS対応 (ACM証明書 + Route53)
- [ ] Datadog LLM Observability統合
- [ ] Auto Scaling設定

