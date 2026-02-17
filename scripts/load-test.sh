#!/bin/bash

# 営業出張サポートAI 負荷テストスクリプト
# 10秒ごとに様々な複雑度のメッセージでAPIを呼び出す
# メッセージの複雑さに応じてエージェントが自律的に2〜4個のツールを呼ぶ

API_URL="${API_URL:-http://localhost:8000}"
INTERVAL=10

# カラー出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%H:%M:%S') $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $(date '+%H:%M:%S') $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%H:%M:%S') $1"
}

log_scenario() {
    echo -e "${YELLOW}[SCENARIO]${NC} $(date '+%H:%M:%S') $1"
}

log_tools() {
    echo -e "${CYAN}[TOOLS]${NC} $1"
}

# シナリオ1: 2ツール呼び出し（規程確認 + 交通検索）
# エージェントは policy_checker と transportation_search を呼ぶ想定
scenario_2tools_transport() {
    log_scenario "2 Tools: Policy + Transport search"
    log_tools "Expected: policy_checker -> transportation_search"
    
    MESSAGE="名古屋に日帰り出張したいのですが、新幹線で行く場合の規程と便を教えてください"
    
    PAYLOAD=$(jq -n --arg message "$MESSAGE" --arg user_id "test-2tools-transport" '{message:$message, user_id:$user_id}')
    RESPONSE=$(curl -s -X POST "$API_URL/api/chat" \
        -H "Content-Type: application/json" \
        -d "$PAYLOAD")
    
    if echo "$RESPONSE" | grep -q "error"; then
        log_error "API error: $RESPONSE"
    else
        log_success "Response received"
    fi
}

# シナリオ2: 2ツール呼び出し（規程確認 + ホテル検索）
# エージェントは policy_checker と hotel_search を呼ぶ想定
scenario_2tools_hotel() {
    log_scenario "2 Tools: Policy + Hotel search"
    log_tools "Expected: policy_checker -> hotel_search"
    
    MESSAGE="大阪出張で1泊する場合、宿泊規程と梅田周辺のホテルを教えてください"
    
    PAYLOAD=$(jq -n --arg message "$MESSAGE" --arg user_id "test-2tools-hotel" '{message:$message, user_id:$user_id}')
    RESPONSE=$(curl -s -X POST "$API_URL/api/chat" \
        -H "Content-Type: application/json" \
        -d "$PAYLOAD")
    
    if echo "$RESPONSE" | grep -q "error"; then
        log_error "API error: $RESPONSE"
    else
        log_success "Response received"
    fi
}

# シナリオ3: 3ツール呼び出し（規程 + 交通 + ホテル）
# エージェントは policy_checker, transportation_search, hotel_search を呼ぶ想定
scenario_3tools() {
    log_scenario "3 Tools: Policy + Transport + Hotel"
    log_tools "Expected: policy_checker -> transportation_search -> hotel_search"
    
    MESSAGE="来週福岡に2泊3日で出張します。東京から飛行機で行って、博多駅近くのホテルに泊まりたいです。規程内で収まりますか？"
    
    PAYLOAD=$(jq -n --arg message "$MESSAGE" --arg user_id "test-3tools" '{message:$message, user_id:$user_id}')
    RESPONSE=$(curl -s -X POST "$API_URL/api/chat" \
        -H "Content-Type: application/json" \
        -d "$PAYLOAD")
    
    if echo "$RESPONSE" | grep -q "error"; then
        log_error "API error: $RESPONSE"
    else
        log_success "Response received"
    fi
}

# シナリオ4: 3ツール呼び出し（条件抽出 + 交通 + ホテル）
# エージェントは condition_extractor, transportation_search, hotel_search を呼ぶ想定
scenario_3tools_extract() {
    log_scenario "3 Tools: Extract + Transport + Hotel"
    log_tools "Expected: condition_extractor -> transportation_search -> hotel_search"
    
    MESSAGE="12月15日から17日まで札幌出張。予算は8万円で、できれば千歳空港からアクセスの良いホテルがいいです"
    
    PAYLOAD=$(jq -n --arg message "$MESSAGE" --arg user_id "test-3tools-extract" '{message:$message, user_id:$user_id}')
    RESPONSE=$(curl -s -X POST "$API_URL/api/chat" \
        -H "Content-Type: application/json" \
        -d "$PAYLOAD")
    
    if echo "$RESPONSE" | grep -q "error"; then
        log_error "API error: $RESPONSE"
    else
        log_success "Response received"
    fi
}

# シナリオ5: 4ツール呼び出し（フル）
# エージェントは policy_checker, condition_extractor, transportation_search, hotel_search を呼ぶ想定
scenario_4tools_full() {
    log_scenario "4 Tools: Full pipeline"
    log_tools "Expected: condition_extractor -> policy_checker -> transportation_search -> hotel_search"
    
    MESSAGE="来月10日から12日まで、東京から広島に出張します。2泊3日で、新幹線のぞみを使って、広島駅から徒歩10分以内のビジネスホテルに泊まりたいです。予算は6万円以内で規程に収まるプランを提案してください"
    
    PAYLOAD=$(jq -n --arg message "$MESSAGE" --arg user_id "test-4tools-full" '{message:$message, user_id:$user_id}')
    RESPONSE=$(curl -s -X POST "$API_URL/api/chat" \
        -H "Content-Type: application/json" \
        -d "$PAYLOAD")
    
    if echo "$RESPONSE" | grep -q "error"; then
        log_error "API error: $RESPONSE"
    else
        log_success "Response received"
    fi
}

# シナリオ6: 4ツール + プラン生成
# エージェントは全ツールを使ってプランまで生成する想定
scenario_4tools_plan() {
    log_scenario "4+ Tools: Full with plan generation"
    log_tools "Expected: condition_extractor -> policy_checker -> transportation_search -> hotel_search -> plan_generator"
    
    MESSAGE="急ぎで仙台出張のプランを作ってください。明後日から1泊2日、東京駅発で新幹線はやぶさ希望。ホテルは仙台駅近くで朝食付き。予算4万円で最適なプランを出してください"
    
    PAYLOAD=$(jq -n --arg message "$MESSAGE" --arg user_id "test-4tools-plan" '{message:$message, user_id:$user_id}')
    RESPONSE=$(curl -s -X POST "$API_URL/api/chat" \
        -H "Content-Type: application/json" \
        -d "$PAYLOAD")
    
    if echo "$RESPONSE" | grep -q "plans"; then
        log_success "Response received with plans!"
    elif echo "$RESPONSE" | grep -q "error"; then
        log_error "API error"
    else
        log_success "Response received"
    fi
}

# シナリオ7: 複雑な条件（4ツール想定）
scenario_complex() {
    log_scenario "4 Tools: Complex requirements"
    log_tools "Expected: Multiple tool calls for complex request"
    
    MESSAGE="名古屋支社との会議のため、12月20日から22日まで2泊3日で出張します。東京から新幹線で行き、名古屋駅から徒歩圏内のホテルに宿泊希望。会議が遅くなる可能性があるので朝食付きで。予算は5万円、規程内で最もコスパの良いプランをお願いします"
    
    PAYLOAD=$(jq -n --arg message "$MESSAGE" --arg user_id "test-complex" '{message:$message, user_id:$user_id}')
    RESPONSE=$(curl -s -X POST "$API_URL/api/chat" \
        -H "Content-Type: application/json" \
        -d "$PAYLOAD")
    
    if echo "$RESPONSE" | grep -q "error"; then
        log_error "API error"
    else
        log_success "Response received"
    fi
}

# シナリオ8: シンプルな規程確認（2ツール）
scenario_simple_policy() {
    log_scenario "2 Tools: Simple policy check"
    log_tools "Expected: condition_extractor -> policy_checker"
    
    MESSAGE="国内出張の日当と宿泊費の上限を教えてください"
    
    PAYLOAD=$(jq -n --arg message "$MESSAGE" --arg user_id "test-simple-policy" '{message:$message, user_id:$user_id}')
    RESPONSE=$(curl -s -X POST "$API_URL/api/chat" \
        -H "Content-Type: application/json" \
        -d "$PAYLOAD")
    
    if echo "$RESPONSE" | grep -q "error"; then
        log_error "API error"
    else
        log_success "Response received"
    fi
}

# ヘルスチェック
health_check() {
    RESPONSE=$(curl -s "$API_URL/health")
    if echo "$RESPONSE" | grep -q "healthy"; then
        return 0
    else
        return 1
    fi
}

# メイン処理
main() {
    echo "========================================"
    echo "  Sales Support AI Load Test"
    echo "  API: $API_URL"
    echo "  Interval: ${INTERVAL}s"
    echo ""
    echo "  Each message triggers 2-4+ tool calls"
    echo "  by the AI agent autonomously"
    echo "========================================"
    echo ""
    
    # ヘルスチェック
    log_info "Checking API health..."
    if ! health_check; then
        log_error "API is not healthy. Exiting."
        exit 1
    fi
    log_success "API is healthy"
    echo ""
    
    # シナリオリスト（ツール呼び出し数順）
    SCENARIOS=(
        "2tools_transport"   # 2 tools
        "2tools_hotel"       # 2 tools
        "simple_policy"      # 2 tools
        "3tools"             # 3 tools
        "3tools_extract"     # 3 tools
        "4tools_full"        # 4 tools
        "4tools_plan"        # 4+ tools
        "complex"            # 4 tools
    )
    SCENARIO_COUNT=${#SCENARIOS[@]}
    
    ITERATION=0
    while true; do
        ITERATION=$((ITERATION + 1))
        echo ""
        echo "========================================"
        echo "  Iteration #$ITERATION"
        echo "========================================"
        
        # ランダムにシナリオを選択
        RANDOM_INDEX=$((RANDOM % SCENARIO_COUNT))
        SELECTED=${SCENARIOS[$RANDOM_INDEX]}
        
        case $SELECTED in
            "2tools_transport")
                scenario_2tools_transport
                ;;
            "2tools_hotel")
                scenario_2tools_hotel
                ;;
            "simple_policy")
                scenario_simple_policy
                ;;
            "3tools")
                scenario_3tools
                ;;
            "3tools_extract")
                scenario_3tools_extract
                ;;
            "4tools_full")
                scenario_4tools_full
                ;;
            "4tools_plan")
                scenario_4tools_plan
                ;;
            "complex")
                scenario_complex
                ;;
        esac
        
        echo ""
        log_info "Waiting ${INTERVAL}s until next iteration..."
        sleep $INTERVAL
    done
}

# Ctrl+C で終了
trap 'echo ""; log_info "Stopping load test..."; exit 0' INT

# 実行
main "$@"
