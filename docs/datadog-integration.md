# Datadog APM & LLM Observability 運用ガイド

## 概要

`backend-python/`（FastAPI + LangChain）を AWS ECS 上で動かし、Datadog APM / LLM Observability を有効化するための運用メモ。

## 現在の構成（実態）

- アプリ本体: `backend-python/`
- 起動: `ddtrace-run uvicorn app.main:app --host 0.0.0.0 --port 8000`
- Datadog API Key: AWS Secrets Manager の `/kentomax/datadog_api_key` を参照
- LLM Observability の `ml_app`: `python-llm-salessupport`

## 必須環境変数（Python）

| 環境変数 | 推奨値 |
|---------|------|
| `DD_SERVICE` | `python-llm-salessupport` |
| `DD_ENV` | `dev` |
| `DD_LLMOBS_ENABLED` | `1` |
| `DD_LLMOBS_ML_APP` | `python-llm-salessupport` |
| `DD_LLMOBS_AGENTLESS_ENABLED` | `1` |
| `DD_API_KEY` | Secrets Manager から注入 |

## デプロイ手順（AWS ECS）

```bash
# 1) 認証
aws sso login --profile kentomax-admin

# 2) イメージ build & push（amd64）
./scripts/build-and-push.sh backend

# 3) ECS サービス再デプロイ
aws ecs update-service \
  --cluster kentomax_sales-support-cluster \
  --service kentomax_sales-support-backend \
  --force-new-deployment \
  --profile kentomax-admin \
  --region ap-northeast-1

# 4) 安定化待ち
aws ecs wait services-stable \
  --cluster kentomax_sales-support-cluster \
  --services kentomax_sales-support-backend \
  --profile kentomax-admin \
  --region ap-northeast-1
```

## 動作確認

```bash
# ヘルスチェック
curl -s "http://kentomax-sales-support-alb-733711893.ap-northeast-1.elb.amazonaws.com/health"

# 包括テスト（Python/AWS）
./scripts/comprehensive-test.sh python \
  http://kentomax-sales-support-alb-733711893.ap-northeast-1.elb.amazonaws.com
```

Datadog 側の確認:

- APM: `service:python-llm-salessupport`
- LLM Observability: `ml_app:python-llm-salessupport`

## Hallucination Detection に関する補足

- Hallucination 評価用の `Prompt` 注釈追加は `backend-python/` のみ実施済み。
- `backend-typescript/` および `backend-python-vertex/` は今回この注釈方式への変更なし。
- 具体的な実装と手順は `docs/llm-observability.md` の「10. Hallucination Detection デモ」を参照。

