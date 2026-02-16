# 作業計画 / 進捗（Python + Vertex AI バックエンド）

最終目的: 既存 `llm-salessupport-demo` と同等の機能/APIを、**Python + Vertex AI (Gemini)** バックエンドとして新規実装し、**GCP Cloud Run** で動かす。

- **重要方針**: まず非計装で正しく動く状態を確立し、その後 **LLM Observability（Datadog）を auto instrumentation で追加**する。
- **ホスティング**: GCP Cloud Run
- **フロント**: 当面ローカル運用（Vite proxyで `/api` をバックエンドへ）
- **API互換（最低限）**:
  - `GET /health`
  - `POST /api/chat`
  - `POST /api/plan/confirm`

参照: `docs/application-logic.md`, `docs/aws-infrastructure.md`

---

## TODO（未着手）

- [ ] Datadog LLM Observability（auto instrumentation）を Cloud Run の `backend-python-vertex` に追加
  - [ ] `ddtrace` 依存追加 + `ddtrace-run` 起動（カスタム計装なし）
  - [ ] `DD_API_KEY` を GCP Secret Manager（`kento-tomax-api-key-for-log`）から注入
  - [ ] `DD_LLMOBS_ML_APP` 等の env 設定（Vertex版と判別できる名前）
  - [ ] Cloud Run へデプロイし、E2E 動作確認（包括テスト + 実UI）
- [ ] Vertex AI（Gemini）で **実際に** ツール呼び出し（function calling）が成立することを確認（Cloud Run上での疎通を優先）
- [ ] 既存フロント互換（request/response shape）を確認し、必要なら調整（Vertex有効時）
- [ ] Terraform（GCP）を apply して Artifact Registry / Cloud Run / IAM を実際に作成
- [ ] Artifact Registry へコンテナを push し、Cloud Run にデプロイして URL を確定
- [ ] `docs/gcp-infrastructure.md` 新設、`README.md` 更新（LLM Obsなし前提）

---

## WIP（作業中）

- [ ] 進捗管理（この `plan.md` を継続更新）
- [ ] Vertex AI SDK / LangChain統合の選定（2026時点の推奨SDKとtool calling実装）
- [ ] Vertex AI tool calling の疎通（ローカル実行 or Cloud Runでの実行確認）

---

## Done（完了）

- [x] まず非計装で成立する状態を確立（バックエンド実装・GCPデプロイ・包括テスト）
- [x] 既存AWS構成の記録（`docs/aws-infrastructure.md`）と既存API形（frontend→backend）を把握
- [x] `backend-python-vertex/` に主要ファイルを追加（構文チェックまで完了）
- [x] `backend-python-vertex/` のAPI雛形（/health, /api/chat, /api/plan/confirm）を追加
- [x] `scripts/comprehensive-test.sh` に customモード（任意URL）とURL上書きを追加
- [x] フォールバックモード（VERTEX_ENABLED=false）でローカルコンテナを起動し、包括テストが全件成功
- [x] Terraform（GCP）骨組みを追加（`infra/terraform/gcp`、fmt/validate済み）

---

## 決定事項（Decision log）

- 2026-02-16: まずは **バックエンドのみ** を GCP Cloud Run へ。フロントはローカルでOK。
- 2026-02-16: 認証方式は未確定 → Cloud Runのサービスアカウント（ADC）でVertex AIにアクセスする前提で設計（鍵ファイル不要）。
- 2026-02-16: **Datadog/LLM Obsは後回し**（まず非計装で成立させる）。
- 2026-02-16: LLM Obs を **auto instrumentation（ddtrace-run + env + Secret Manager）** で追加する。
- 2026-02-16: GCP Project ID: `mcse-sandbox` / Vertex region: `asia-northeast1` / model: `gemini-2.5-flash`
- 2026-02-16: 命名規則: GCPはリソース名に `_` が使えないケースが多いため、接頭辞は **`kentomax-`（ハイフン）** を採用（AWSの `kentomax_` と同趣旨で統一）
- 2026-02-16: ラベル値制約: GCPのlabel valueは `.` が使えないため、`user=kento.tomatsu` は **`user=kento-tomatsu` にサニタイズ**して付与（値の同一性は運用上の意味として保持）

