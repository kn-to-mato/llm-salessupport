# backend-python-vertex

既存デモ（`llm-salessupport-demo`）と同等のAPIを、**Python + Vertex AI (Gemini)** で実装するバックエンドです。

## 目的

- `GET /health`
- `POST /api/chat`
- `POST /api/plan/confirm`

を既存フロント（`frontend/`）からそのまま呼べる形で提供します。

## 重要方針

- **カスタム計装は入れません**（コードに手を入れず、`ddtrace-run` による auto instrumentation で LLM Observability を有効化します）。

## ローカル起動（想定）

前提: Vertex AI へアクセスできる認証（ADC）が必要です。

- 例: `gcloud auth application-default login`
- `GOOGLE_CLOUD_PROJECT` / `GOOGLE_CLOUD_LOCATION` を設定

```bash
cd backend-python-vertex
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

export GOOGLE_CLOUD_PROJECT=mcse-sandbox
export GOOGLE_CLOUD_LOCATION=asia-northeast1
export VERTEX_MODEL=gemini-2.5-flash
export VERTEX_ENABLED=true

ddtrace-run uvicorn app.main:app --reload --port 8001
```

フロントは `VITE_BACKEND_URL` で接続先を変えられます。

```bash
cd ../frontend
VITE_BACKEND_URL=http://localhost:8001 npm run dev
```

## Vertex AI をまだ設定していない場合（フォールバック）

Vertex AI の認証（ADC）やIAM設定が未完了でも、API互換の確認を先に進められるように
`VERTEX_ENABLED=false` で **フォールバック動作**できます（簡易な規則ベース応答＋モックツール）。

```bash
export VERTEX_ENABLED=false
ddtrace-run uvicorn app.main:app --reload --port 8001
```

## Datadog LLM Observability（auto instrumentation）

Datadog LLM Observability を有効化する場合は、環境変数を設定して `ddtrace-run` で起動します。

- `DD_SITE=datadoghq.com`（US1）
- `DD_LLMOBS_ENABLED=1`
- `DD_LLMOBS_AGENTLESS_ENABLED=1`
- `DD_LLMOBS_ML_APP=python-llm-salessupport-vertex`
- `DD_API_KEY`（ローカルでは環境変数、Cloud Run では Secret Manager から注入）

