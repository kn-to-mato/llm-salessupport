# GCP インフラ構成（Cloud Run + Vertex AI）

このドキュメントは `backend-python-vertex/`（Python + Vertex AI/Gemini）の **GCPデプロイ構成**をまとめます。

## 前提

- Project ID: `mcse-sandbox`
- Region: `asia-northeast1`
- Model: `gemini-2.5-flash`
- **Observability/計装**: Datadog **LLM Observability を auto instrumentation で有効化**（`DD_API_KEY` は Secret Manager 参照）

## 命名・ラベル運用（重要）

- **接頭辞**: GCPのリソース名は `_` を許容しないケースが多いため、AWSでの `kentomax_` と同趣旨で **`kentomax-`（ハイフン）** を採用。
- **ラベル**: GCPのlabel valueは `.` を許容しないため、`user=kento.tomatsu` は **`user=kento-tomatsu` にサニタイズ**して付与（意味は同一として扱う）。

## 構成（Terraform）

Terraformコードは `infra/terraform/gcp/`。

作成リソース（最小）:

- Artifact Registry（Docker）
  - repo: `kentomax-sales-support`
- Cloud Run サービス（バックエンド）
  - service: `kentomax-sales-support-backend-vertex`
  - public invoker: `allUsers`（デモ用途。必要なら制限）
- Service Account
  - `kentomax-sales-support-cr`
- IAM
  - Cloud Run runtime SA: `roles/aiplatform.user`
  - Cloud Run service agent: Artifact Registry pull (`roles/artifactregistry.reader`)
  - Cloud Run runtime SA: Secret Manager read (`roles/secretmanager.secretAccessor`) for `DD_API_KEY`

## デプロイ手順

### 1) 認証（gcloud）

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project mcse-sandbox
```

### 2) Terraform apply（2段階）

最初に repo/IAM を作ってから、イメージ push 後に Cloud Run を作成します。

```bash
cd infra/terraform/gcp

# 初回: deploy_cloud_run=false（repo/IAMまで）
terraform apply
```

### 3) Docker build & push（Artifact Registry）

```bash
docker build --platform linux/amd64 -t kentomax/llm-salessupport-vertex-backend:local ./backend-python-vertex
docker tag kentomax/llm-salessupport-vertex-backend:local \
  asia-northeast1-docker.pkg.dev/mcse-sandbox/kentomax-sales-support/backend-python-vertex:latest

# docker-credential-gcloud が PATH に無い場合があるため、PATH にSDK binを追加して push
export PATH="$HOME/google-cloud-sdk/bin:$PATH"
gcloud auth print-access-token | docker login -u oauth2accesstoken --password-stdin https://asia-northeast1-docker.pkg.dev
docker push asia-northeast1-docker.pkg.dev/mcse-sandbox/kentomax-sales-support/backend-python-vertex:latest
```

### 4) Cloud Run デプロイ（Terraform）

`infra/terraform/gcp/terraform.tfvars` を以下に更新:

- `deploy_cloud_run=true`
- `container_image=asia-northeast1-docker.pkg.dev/...:latest`

```bash
cd infra/terraform/gcp
terraform apply
terraform output cloud_run_url
```

### 5) 動作確認

```bash
./scripts/comprehensive-test.sh custom "$(cd infra/terraform/gcp && terraform output -raw cloud_run_url)"
```

## Datadog LLM Observability（auto instrumentation）

Cloud Run の環境変数として以下を設定し、アプリ起動は `ddtrace-run` を使用します（コード側にカスタム計装は入れません）。

- `DD_API_KEY`: Secret Manager の `kento-tomax-api-key-for-log` から注入
- `DD_SITE`: `datadoghq.com`（US1）
- `DD_LLMOBS_ENABLED=1`
- `DD_LLMOBS_AGENTLESS_ENABLED=1`
- `DD_LLMOBS_ML_APP=python-llm-salessupport-vertex`
- `DD_SERVICE=kentomax-sales-support-backend-vertex`
- `DD_ENV=dev`

