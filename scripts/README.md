## scripts/ の役割まとめ

### テスト系
- **`comprehensive-test.sh`**: 1回で複数の代表入力を流す「包括E2E」テスト。`dual` モードで LangChain(AWS) と Vertex(Cloud Run) に同じテストセットを投げられる。
- **`test-prompts.sh`**: Datadog LLM Observability の「ツール呼び出しパターン差」を確認するためのデモ用プロンプトセット（4パターン）。
- **`test-company-tags.sh`**: `company_name` を変えながら大量リクエストを投げ、Datadog側でタグフィルタが効くことを確認する。
- **`load-test.sh`**: 10秒間隔でランダムなシナリオを回し続ける簡易負荷テスト（止めるまで動く）。

### 開発/運用系
- **`run-dual-frontend.sh`**: ローカルフロントを2つ同時起動（例: 5173=LangChain, 5174=Vertex）。`VITE_BACKEND_URL` を変えて並べて確認する用途。
- **`setup-local.sh`**: ローカル開発の初期セットアップ（DB起動 + `backend-python` venv + `frontend` npm install）。
- **`build-and-push.sh`**: AWS(ECR) へ `backend-python` / `frontend` を amd64 で build & push（`aws sso login` 前提）。

### 重複/整理の考え方（提案）
- **基本は `comprehensive-test.sh` に寄せる**: CIや手動回帰の入口はこれ1本にし、他は目的別（負荷/タグ/デモ）に残す。
- **`test-prompts.sh` と `comprehensive-test.sh` の重複**: どちらも `/api/chat` に投げるが、狙いが違う（前者=LLM Obsデモ、後者=回帰/網羅）ので両方残すのが自然。
- **`load-test.sh` は目的が別**（継続実行）なので残す。ただしJSON文字列生成は壊れやすいので `jq` 化してある。
