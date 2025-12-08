#!/bin/bash
# LLM Observability デモ用テストプロンプト
# 
# 目的: ツール呼び出しパターンの違いをDatadog LLM Obsで確認する
#
# 使い方:
#   ./scripts/test-prompts.sh all    # 全ツール呼び出しパターン
#   ./scripts/test-prompts.sh skip   # 一部ツールをスキップするパターン

API_URL="${API_URL:-http://localhost:8000}"
SESSION_ID=""

# バックエンド種別を判定（ポート番号から）
if [[ "$API_URL" == *":8000"* ]]; then
    BACKEND_TYPE="Python"
    BACKEND_COLOR='\033[0;33m'  # Yellow for Python
elif [[ "$API_URL" == *":3000"* ]]; then
    BACKEND_TYPE="TypeScript"
    BACKEND_COLOR='\033[0;36m'  # Cyan for TypeScript
else
    BACKEND_TYPE="Unknown"
    BACKEND_COLOR='\033[0;37m'
fi

# 色付き出力
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# バックエンド表示
echo ""
echo -e "${BACKEND_COLOR}[${BACKEND_TYPE}]${NC} Backend: ${API_URL}"
echo ""

send_message() {
    local message="$1"
    local description="$2"
    
    # メッセージにバックエンド種別のプレフィックスを付与
    local prefixed_message="[${BACKEND_TYPE}] ${message}"
    
    echo -e "${BLUE}-------------------------------------------${NC}"
    echo -e "${GREEN}[送信] ${description}${NC}"
    echo -e "${YELLOW}メッセージ: ${prefixed_message}${NC}"
    echo ""
    
    if [ -z "$SESSION_ID" ]; then
        # 新規セッション
        response=$(curl -s -X POST "${API_URL}/api/chat" \
            -H "Content-Type: application/json" \
            -d "{
                \"user_id\": \"demo-user\",
                \"message\": \"${prefixed_message}\"
            }")
    else
        # 既存セッション継続
        response=$(curl -s -X POST "${API_URL}/api/chat" \
            -H "Content-Type: application/json" \
            -d "{
                \"user_id\": \"demo-user\",
                \"session_id\": \"${SESSION_ID}\",
                \"message\": \"${prefixed_message}\"
            }")
    fi
    
    # セッションIDを抽出
    SESSION_ID=$(echo "$response" | jq -r '.session_id')
    
    # レスポンスを表示
    echo "レスポンス:"
    echo "$response" | jq -r '.messages[0].content' 2>/dev/null | head -20
    echo ""
    
    # プラン数を表示
    plan_count=$(echo "$response" | jq -r '.plans | length' 2>/dev/null)
    if [ "$plan_count" != "null" ] && [ "$plan_count" -gt 0 ]; then
        echo -e "${GREEN}生成されたプラン数: ${plan_count}${NC}"
    fi
    
    echo ""
}

# ============================================================
# パターン1: 全ツールが呼ばれるケース
# ============================================================
test_all_tools() {
    echo ""
    echo -e "${GREEN}============================================================${NC}"
    echo -e "${BACKEND_COLOR}[${BACKEND_TYPE}]${NC} ${GREEN}パターン1: 全ツールが呼ばれるケース${NC}"
    echo -e "${GREEN}============================================================${NC}"
    echo ""
    echo "期待されるツール呼び出し:"
    echo "  - transportation_search (交通検索)"
    echo "  - hotel_search (ホテル検索)"
    echo "  - plan_generator (プラン生成)"
    echo "  - policy_checker (規程チェック) ※LangChain Agent経由"
    echo ""
    
    SESSION_ID=""
    
    # Step 1: 全条件を一度に指定 + 規程チェックを依頼
    send_message "東京から大阪に出張したいです。12月9日出発、12月10日帰着で、新幹線を使いたいです。予算は5万円です。この条件で社内規程に違反しないか確認して、プランを提案してください。" \
        "Step 1: 全条件指定 + 規程チェック依頼"
    
    echo -e "${GREEN}>>> Datadog LLM Obs で確認:${NC}"
    echo "  - travel-support-agent 配下に複数のWorkflowとToolがネストされているはず"
    echo "  - plan_generation workflow 内に transportation_search, hotel_search, plan_generator"
    echo ""
}

# ============================================================
# パターン2: 一部ツールがスキップされるケース
# ============================================================
test_skip_tool() {
    echo ""
    echo -e "${YELLOW}============================================================${NC}"
    echo -e "${BACKEND_COLOR}[${BACKEND_TYPE}]${NC} ${YELLOW}パターン2: 一部ツールがスキップされるケース (日帰り)${NC}"
    echo -e "${YELLOW}============================================================${NC}"
    echo ""
    echo "期待されるツール呼び出し:"
    echo "  - transportation_search (交通検索) ✓"
    echo "  - hotel_search (ホテル検索) ✗ スキップ（日帰りのため）"
    echo "  - plan_generator (プラン生成) ✗ スキップ（return_dateがないため）"
    echo ""
    
    SESSION_ID=""
    
    # Step 1: 日帰り出張（ホテル不要）
    send_message "東京から名古屋に日帰りで出張したいです。12月15日に行って、当日中に戻ります。新幹線で移動したいです。" \
        "Step 1: 日帰り出張（ホテル検索がスキップされる）"
    
    echo -e "${YELLOW}>>> Datadog LLM Obs で確認:${NC}"
    echo "  - hotel_search ツールが呼ばれていないはず"
    echo "  - Tool Selection Evaluation で検出可能"
    echo ""
}

# ============================================================
# パターン3: 条件が不足しているケース
# ============================================================
test_incomplete() {
    echo ""
    echo -e "${YELLOW}============================================================${NC}"
    echo -e "${BACKEND_COLOR}[${BACKEND_TYPE}]${NC} ${YELLOW}パターン3: 条件不足でツールが呼ばれないケース${NC}"
    echo -e "${YELLOW}============================================================${NC}"
    echo ""
    echo "期待されるツール呼び出し:"
    echo "  - すべてスキップ（条件が揃っていないため）"
    echo ""
    
    SESSION_ID=""
    
    # Step 1: 曖昧な依頼
    send_message "来月どこかに出張するかも。まだ決まってないけど。" \
        "Step 1: 曖昧な依頼（ツール呼び出しなし）"
    
    echo -e "${YELLOW}>>> Datadog LLM Obs で確認:${NC}"
    echo "  - langchain_agent_execution 内でツール呼び出しがないはず"
    echo "  - condition_extraction のみが実行される"
    echo ""
}

# ============================================================
# パターン4: 複数ターンで条件を追加
# ============================================================
test_multi_turn() {
    echo ""
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${BLUE} パターン4: 複数ターンで条件追加 → 最終的に全ツール呼び出し${NC}"
    echo -e "${BLUE}============================================================${NC}"
    echo ""
    
    SESSION_ID=""
    
    # Step 1
    send_message "大阪に出張したいです。" \
        "Step 1: 目的地のみ"
    
    sleep 2
    
    # Step 2
    send_message "東京から行きます。新幹線で。" \
        "Step 2: 出発地と交通手段追加"
    
    sleep 2
    
    # Step 3
    send_message "12月20日出発、12月21日帰着でお願いします。" \
        "Step 3: 日程追加 → プラン生成トリガー"
    
    echo -e "${BLUE}>>> Datadog LLM Obs で確認:${NC}"
    echo "  - Session ID でフィルタして、3つのトレースを確認"
    echo "  - 最後のトレースでのみ plan_generation workflow が実行される"
    echo ""
}

# メイン処理
case "${1:-all}" in
    all)
        test_all_tools
        ;;
    skip)
        test_skip_tool
        ;;
    incomplete)
        test_incomplete
        ;;
    multi)
        test_multi_turn
        ;;
    demo)
        echo "デモ用: 全パターンを順番に実行します"
        echo "各パターンの間に10秒待機します"
        echo ""
        test_all_tools
        sleep 10
        test_skip_tool
        sleep 10
        test_incomplete
        sleep 10
        test_multi_turn
        ;;
    *)
        echo "Usage: $0 {all|skip|incomplete|multi|demo}"
        echo ""
        echo "  all        - 全ツールが呼ばれるパターン"
        echo "  skip       - 一部ツールがスキップされるパターン（日帰り）"
        echo "  incomplete - 条件不足でツールが呼ばれないパターン"
        echo "  multi      - 複数ターンで条件追加"
        echo "  demo       - 全パターンを順番に実行"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}テスト完了${NC}"
echo ""
echo "Datadog LLM Observability で確認:"
echo "  https://app.datadoghq.com/llm/traces"
echo ""
echo "フィルタ:"
echo "  - ml_app:llm-salessupport"
echo "  - env:dev"
echo ""


