# Datadog APM & LLM Observability 導入ガイド

## 概要

このドキュメントでは、ECS on Fargate上で動作するPythonアプリケーション（FastAPI + LangChain）に対して、Datadog APMおよびLLM Observabilityを導入する手順を説明します。

## 前提条件

- AWS ECS on Fargateでアプリケーションが稼働中
- Datadog アカウントを持っている
- Datadog API Keyを取得済み

## アーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│  ECS Fargate Task                                           │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Backend Container                                   │   │
│  │                                                      │   │
│  │  ddtrace-run uvicorn app.main:app ...               │   │
│  │       │                                              │   │
│  │       ├── APM Traces (リクエスト/レスポンス追跡)      │   │
│  │       └── LLM Obs (LLM呼び出し追跡)                  │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │                                   │
└─────────────────────────┼───────────────────────────────────┘
                          │ HTTPS (Agentless)
                          ▼
                    Datadog Backend
                    (APM + LLM Observability)
```

## 導入手順

### Step 1: ddtrace パッケージの追加 ✅

**目的**: Datadogのトレーシングライブラリをインストールする

**変更ファイル**: `backend/requirements.txt`

**追加内容**:
```
# Datadog APM & LLM Observability
# LangChain integration requires >= 2.9.0, using 3.11.0+ for better stability
ddtrace>=3.11.0
```

**バージョン選定の理由**:
- LangChain integration: ddtrace >= 2.9.0 が必要
- 一部のLLMフレームワーク（Bedrock, Anthropic等）: >= 2.15.0 が必要
- 安定性を考慮して **3.11.0以上** を指定
- 実際にインストールされるのは最新版（執筆時点で4.0.0）

**説明**:
- `ddtrace` はDatadog公式のPython APMライブラリ
- 自動計装（Auto-instrumentation）により、コード変更なしで多くのフレームワーク・ライブラリをトレース可能
- 対応フレームワーク: FastAPI, SQLAlchemy, httpx, OpenAI, LangChain など

**参考ドキュメント**:
- Python APM: https://docs.datadoghq.com/tracing/trace_collection/automatic_instrumentation/dd_libraries/python/
- LLM Obs Auto Instrumentation: https://docs.datadoghq.com/llm_observability/instrumentation/auto_instrumentation/?tab=python

---

### Step 2: Dockerfile の CMD を変更 ✅

**目的**: アプリケーション起動時に `ddtrace-run` でラップする

**変更ファイル**: `backend/Dockerfile`

**変更前**:
```dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**変更後**:
```dockerfile
CMD ["ddtrace-run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**説明**:
- `ddtrace-run` はDatadogが提供するラッパーコマンド
- このコマンド経由で起動することで、自動計装が有効になる
- Pythonプロセスの起動前に、対応ライブラリへのパッチが適用される

---

### Step 3: 環境変数の設定（ECSタスク定義）

**目的**: Datadogへの接続情報とLLM Observabilityの有効化

**設定する環境変数**:

| 環境変数 | 値 | 説明 |
|---------|-----|------|
| `DD_SERVICE` | `kentomax-sales-support-backend` | サービス名（Datadog上での識別名） |
| `DD_ENV` | `dev` | 環境名（dev/staging/production） |
| `DD_VERSION` | `1.0.0` | アプリケーションバージョン |
| `DD_TRACE_ENABLED` | `true` | APMトレースの有効化 |
| `DD_LLMOBS_ENABLED` | `1` | LLM Observabilityの有効化 |
| `DD_LLMOBS_ML_APP` | `kentomax-sales-support` | LLM Obsでのアプリ識別名 |
| `DD_LLMOBS_AGENTLESS_ENABLED` | `1` | Agentlessモードの有効化（Fargate向け） |
| `DD_API_KEY` | `(Secrets Managerから取得)` | Datadog API Key |

**Agentlessモードについて**:
- 通常、Datadog APMはDatadog Agentを経由してデータを送信する
- Fargateではサイドカーとしてエージェントを追加する方法もあるが、Agentlessならエージェント不要
- LLM Observabilityは `DD_LLMOBS_AGENTLESS_ENABLED=1` でAgentless送信が可能

---

### Step 4: Secrets ManagerにDatadog API Keyを保存

**目的**: API Keyを安全に管理する

**シークレット名**: `kentomax_datadog-api-key`（仮）

**手順**:
```bash
aws secretsmanager create-secret \
  --name kentomax_datadog-api-key \
  --secret-string '{"DD_API_KEY":"your-datadog-api-key"}' \
  --tags Key=please_keep_it,Value=true Key=user,Value=kento.tomatsu \
  --profile kentomax-admin \
  --region ap-northeast-1
```

---

### Step 5: ECSタスク定義の更新

**目的**: 新しい環境変数を追加したタスク定義を登録

（詳細は実行時に追記）

---

### Step 6: Dockerイメージのビルド＆プッシュ

**目的**: ddtrace入りの新しいイメージをECRにアップロード

```bash
# ECRログイン
aws ecr get-login-password --region ap-northeast-1 --profile kentomax-admin | \
  docker login --username AWS --password-stdin 369042512949.dkr.ecr.ap-northeast-1.amazonaws.com

# ビルド
docker build --platform linux/amd64 -t kentomax/sales-support/backend:latest ./backend

# タグ付け
docker tag kentomax/sales-support/backend:latest \
  369042512949.dkr.ecr.ap-northeast-1.amazonaws.com/kentomax/sales-support/backend:latest

# プッシュ
docker push 369042512949.dkr.ecr.ap-northeast-1.amazonaws.com/kentomax/sales-support/backend:latest
```

---

### Step 7: ECSサービスの更新

**目的**: 新しいタスク定義でサービスを再デプロイ

```bash
aws ecs update-service \
  --cluster kentomax_sales-support-cluster \
  --service kentomax_sales-support-backend \
  --force-new-deployment \
  --profile kentomax-admin \
  --region ap-northeast-1
```

---

## 確認方法

### Datadog APM
1. Datadog Console → APM → Services
2. `kentomax-sales-support-backend` サービスが表示されることを確認
3. トレースをクリックして詳細を確認

### LLM Observability
1. Datadog Console → LLM Observability
2. `kentomax-sales-support` アプリが表示されることを確認
3. LLM呼び出しのトレース、入力/出力、トークン数などが記録されていることを確認

---

## 現在のステータス

- [x] Step 1: ddtrace パッケージの追加 (2024-12-02)
- [x] Step 2: Dockerfile の CMD を変更 (2024-12-02)
- [ ] Step 3: 環境変数の設定
- [ ] Step 4: Secrets ManagerにAPI Key保存
- [ ] Step 5: ECSタスク定義の更新
- [ ] Step 6: Dockerイメージのビルド＆プッシュ
- [ ] Step 7: ECSサービスの更新

---

## 作業ログ

### 2024-12-02

**Step 1 完了**
- `backend/requirements.txt` に `ddtrace>=3.11.0` を追加
- バージョン選定理由: LangChain integration (>=2.9.0) + 安定性を考慮
- ローカルvenvにもインストール確認済み（ddtrace 4.0.0）

**Step 2 完了**
- `backend/Dockerfile` の CMD を `ddtrace-run` でラップ
- 変更: `CMD ["ddtrace-run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]`

**次のステップ**
- ローカルでの動作確認（ddtrace-run + 環境変数設定）
- Step 3以降の実施

---

## 補足: Unified Service Tagging

`DD_SERVICE`, `DD_ENV`, `DD_VERSION` の3つは「Unified Service Tagging」と呼ばれ、Datadog全体で一貫したサービス識別を実現します。

- **DD_SERVICE**: サービス名（マイクロサービス単位）
- **DD_ENV**: 環境（production, staging, development）
- **DD_VERSION**: デプロイバージョン

これらを設定することで、APM、Logs、Infrastructure間でデータを関連付けられます。

参考: https://docs.datadoghq.com/getting_started/tagging/unified_service_tagging/

