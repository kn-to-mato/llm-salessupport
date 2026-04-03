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

## デモ用URL（ブラウザから呼び出す）

### LangChain版（AWS / ALB）

- **URL**: `http://kentomax-sales-support-alb-733711893.ap-northeast-1.elb.amazonaws.com`

注: ALBのSGが **IP/32制限** になっているため、アクセスできない場合は `docs/aws-infrastructure.md` のSG情報（`kentomax_sales-support-alb-sg`）に従って、許可IPを更新してください（0.0.0.0/0は禁止）。

### Vertex版（バックエンド: Cloud Run / フロント: ローカル）

- **Cloud Run backend URL**: `https://kentomax-sales-support-backend-vertex-n4ow3sy4fq-an.a.run.app`
- **ローカルフロントURL**: `http://localhost:5173`

ローカル起動コマンド（フロントのみ）:

```bash
cd frontend
npm install
VITE_BACKEND_URL=https://kentomax-sales-support-backend-vertex-n4ow3sy4fq-an.a.run.app npm run dev
```

動作確認（任意）:

```bash
./scripts/comprehensive-test.sh custom "https://kentomax-sales-support-backend-vertex-n4ow3sy4fq-an.a.run.app"
```

---

## TODO（現時点）

- [ ] 追加の改善タスクが発生したら追記

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
- [x] Vertex 版への Datadog LLM Observability auto instrumentation（`ddtrace-run` + 環境変数）を反映
- [x] `docs/gcp-infrastructure.md` / `README.md` を Vertex 運用前提に更新
- [x] Python(LangChain) 側で Hallucination Detection 用 `Prompt` 注釈を通常フローに追加
- [x] Hallucination 用入力を `scripts/comprehensive-test.sh`（テスト9）へ追加し、自然文ベースへ調整
- [x] ECS 再デプロイ後に包括テストを再実行し、Datadog 上の評価確認手順を整理

---

## 決定事項（Decision log）

- 2026-02-16: まずは **バックエンドのみ** を GCP Cloud Run へ。フロントはローカルでOK。
- 2026-02-16: 認証方式は未確定 → Cloud Runのサービスアカウント（ADC）でVertex AIにアクセスする前提で設計（鍵ファイル不要）。
- 2026-02-16: **Datadog/LLM Obsは後回し**（まず非計装で成立させる）。
- 2026-02-16: LLM Obs を **auto instrumentation（ddtrace-run + env + Secret Manager）** で追加する。
- 2026-02-16: GCP Project ID: `mcse-sandbox` / Vertex region: `asia-northeast1` / model: `gemini-2.5-flash`
- 2026-02-16: 命名規則: GCPはリソース名に `_` が使えないケースが多いため、接頭辞は **`kentomax-`（ハイフン）** を採用（AWSの `kentomax_` と同趣旨で統一）
- 2026-02-16: ラベル値制約: GCPのlabel valueは `.` が使えないため、`user=kento.tomatsu` は **`user=kento-tomatsu` にサニタイズ**して付与（値の同一性は運用上の意味として保持）

