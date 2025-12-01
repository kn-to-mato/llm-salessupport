#!/bin/bash

# 営業出張サポートAI 負荷テストスクリプト
# 10秒ごとに様々なシナリオでAPIを呼び出す

API_URL="${API_URL:-http://localhost:8000}"
INTERVAL=10

# カラー出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

# シナリオ1: 2回のエージェント呼び出し（シンプル）
scenario_simple() {
    log_scenario "Simple: 2 turns - Quick question and answer"
    
    # 1回目: 初期質問
    RESPONSE=$(curl -s -X POST "$API_URL/api/chat" \
        -H "Content-Type: application/json" \
        -d '{"message": "名古屋に日帰り出張したいです", "user_id": "test-user-simple"}')
    
    SESSION_ID=$(echo $RESPONSE | grep -o '"session_id":"[^"]*"' | cut -d'"' -f4)
    
    if [ -z "$SESSION_ID" ]; then
        log_error "Failed to get session_id"
        return 1
    fi
    
    log_info "Session started: $SESSION_ID"
    sleep 1
    
    # 2回目: 日程指定
    RESPONSE=$(curl -s -X POST "$API_URL/api/chat" \
        -H "Content-Type: application/json" \
        -d "{\"session_id\": \"$SESSION_ID\", \"message\": \"明日の朝出発で、新幹線希望です\", \"user_id\": \"test-user-simple\"}")
    
    if echo "$RESPONSE" | grep -q "plans"; then
        log_success "Simple scenario completed with plans"
    else
        log_info "Simple scenario completed (no plans yet)"
    fi
}

# シナリオ2: 3回のエージェント呼び出し（標準）
scenario_standard() {
    log_scenario "Standard: 3 turns - Osaka trip with details"
    
    # 1回目: 初期質問
    RESPONSE=$(curl -s -X POST "$API_URL/api/chat" \
        -H "Content-Type: application/json" \
        -d '{"message": "来週大阪に出張したいです。東京発で2泊3日", "user_id": "test-user-standard"}')
    
    SESSION_ID=$(echo $RESPONSE | grep -o '"session_id":"[^"]*"' | cut -d'"' -f4)
    
    if [ -z "$SESSION_ID" ]; then
        log_error "Failed to get session_id"
        return 1
    fi
    
    log_info "Session started: $SESSION_ID"
    sleep 1
    
    # 2回目: 日程と予算
    RESPONSE=$(curl -s -X POST "$API_URL/api/chat" \
        -H "Content-Type: application/json" \
        -d "{\"session_id\": \"$SESSION_ID\", \"message\": \"12月15日から17日で、予算は5万円以内です\", \"user_id\": \"test-user-standard\"}")
    
    log_info "Added date and budget"
    sleep 1
    
    # 3回目: 交通手段指定
    RESPONSE=$(curl -s -X POST "$API_URL/api/chat" \
        -H "Content-Type: application/json" \
        -d "{\"session_id\": \"$SESSION_ID\", \"message\": \"新幹線のぞみで行きたいです\", \"user_id\": \"test-user-standard\"}")
    
    if echo "$RESPONSE" | grep -q "plans"; then
        log_success "Standard scenario completed with plans"
    else
        log_info "Standard scenario completed"
    fi
}

# シナリオ3: 4回のエージェント呼び出し（詳細）
scenario_detailed() {
    log_scenario "Detailed: 4 turns - Fukuoka trip with negotiation"
    
    # 1回目: 初期質問
    RESPONSE=$(curl -s -X POST "$API_URL/api/chat" \
        -H "Content-Type: application/json" \
        -d '{"message": "福岡に出張に行きたいのですが", "user_id": "test-user-detailed"}')
    
    SESSION_ID=$(echo $RESPONSE | grep -o '"session_id":"[^"]*"' | cut -d'"' -f4)
    
    if [ -z "$SESSION_ID" ]; then
        log_error "Failed to get session_id"
        return 1
    fi
    
    log_info "Session started: $SESSION_ID"
    sleep 1
    
    # 2回目: 基本情報
    RESPONSE=$(curl -s -X POST "$API_URL/api/chat" \
        -H "Content-Type: application/json" \
        -d "{\"session_id\": \"$SESSION_ID\", \"message\": \"東京から、来月の10日から12日の2泊3日です\", \"user_id\": \"test-user-detailed\"}")
    
    log_info "Added basic info"
    sleep 1
    
    # 3回目: 予算と希望
    RESPONSE=$(curl -s -X POST "$API_URL/api/chat" \
        -H "Content-Type: application/json" \
        -d "{\"session_id\": \"$SESSION_ID\", \"message\": \"予算は7万円くらいで、できれば飛行機がいいです\", \"user_id\": \"test-user-detailed\"}")
    
    log_info "Added budget and preference"
    sleep 1
    
    # 4回目: 追加要望
    RESPONSE=$(curl -s -X POST "$API_URL/api/chat" \
        -H "Content-Type: application/json" \
        -d "{\"session_id\": \"$SESSION_ID\", \"message\": \"ホテルは博多駅近くがいいです。朝食付きだとなお良い\", \"user_id\": \"test-user-detailed\"}")
    
    if echo "$RESPONSE" | grep -q "plans"; then
        log_success "Detailed scenario completed with plans"
    else
        log_info "Detailed scenario completed"
    fi
}

# シナリオ4: 5回のエージェント呼び出し（プラン確定まで）
scenario_full() {
    log_scenario "Full: 5 turns - Complete flow with plan confirmation"
    
    # 1回目: 初期質問
    RESPONSE=$(curl -s -X POST "$API_URL/api/chat" \
        -H "Content-Type: application/json" \
        -d '{"message": "仙台に出張したいです", "user_id": "test-user-full"}')
    
    SESSION_ID=$(echo $RESPONSE | grep -o '"session_id":"[^"]*"' | cut -d'"' -f4)
    
    if [ -z "$SESSION_ID" ]; then
        log_error "Failed to get session_id"
        return 1
    fi
    
    log_info "Session started: $SESSION_ID"
    sleep 1
    
    # 2回目: 出発地
    RESPONSE=$(curl -s -X POST "$API_URL/api/chat" \
        -H "Content-Type: application/json" \
        -d "{\"session_id\": \"$SESSION_ID\", \"message\": \"東京駅から出発します\", \"user_id\": \"test-user-full\"}")
    
    log_info "Added departure"
    sleep 1
    
    # 3回目: 日程
    RESPONSE=$(curl -s -X POST "$API_URL/api/chat" \
        -H "Content-Type: application/json" \
        -d "{\"session_id\": \"$SESSION_ID\", \"message\": \"12月20日から21日の1泊2日です\", \"user_id\": \"test-user-full\"}")
    
    log_info "Added dates"
    sleep 1
    
    # 4回目: 予算と交通
    RESPONSE=$(curl -s -X POST "$API_URL/api/chat" \
        -H "Content-Type: application/json" \
        -d "{\"session_id\": \"$SESSION_ID\", \"message\": \"予算4万円、はやぶさで行きたいです\", \"user_id\": \"test-user-full\"}")
    
    log_info "Added budget and transport"
    
    # プランIDを取得
    PLAN_ID=$(echo $RESPONSE | grep -o '"plan_id":"[^"]*"' | head -1 | cut -d'"' -f4)
    sleep 1
    
    # 5回目: プラン確定（プランがあれば）
    if [ -n "$PLAN_ID" ]; then
        RESPONSE=$(curl -s -X POST "$API_URL/api/plan/confirm" \
            -H "Content-Type: application/json" \
            -d "{\"session_id\": \"$SESSION_ID\", \"plan_id\": \"$PLAN_ID\", \"user_id\": \"test-user-full\"}")
        
        if echo "$RESPONSE" | grep -q "confirmed"; then
            log_success "Full scenario completed with plan confirmation"
        else
            log_info "Plan confirmation response received"
        fi
    else
        log_info "Full scenario completed (no plan to confirm)"
    fi
}

# シナリオ5: 札幌出張（飛行機）
scenario_sapporo() {
    log_scenario "Sapporo: 3 turns - Flight to Hokkaido"
    
    # 1回目
    RESPONSE=$(curl -s -X POST "$API_URL/api/chat" \
        -H "Content-Type: application/json" \
        -d '{"message": "札幌に3泊4日で出張したいです。予算は10万円", "user_id": "test-user-sapporo"}')
    
    SESSION_ID=$(echo $RESPONSE | grep -o '"session_id":"[^"]*"' | cut -d'"' -f4)
    log_info "Session started: $SESSION_ID"
    sleep 1
    
    # 2回目
    RESPONSE=$(curl -s -X POST "$API_URL/api/chat" \
        -H "Content-Type: application/json" \
        -d "{\"session_id\": \"$SESSION_ID\", \"message\": \"東京から12月25日出発、28日帰着です\", \"user_id\": \"test-user-sapporo\"}")
    
    log_info "Added dates"
    sleep 1
    
    # 3回目
    RESPONSE=$(curl -s -X POST "$API_URL/api/chat" \
        -H "Content-Type: application/json" \
        -d "{\"session_id\": \"$SESSION_ID\", \"message\": \"飛行機で行きます。ホテルはすすきの周辺希望\", \"user_id\": \"test-user-sapporo\"}")
    
    if echo "$RESPONSE" | grep -q "plans"; then
        log_success "Sapporo scenario completed with plans"
    else
        log_info "Sapporo scenario completed"
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
    
    # シナリオリスト
    SCENARIOS=("simple" "standard" "detailed" "full" "sapporo")
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
            "simple")
                scenario_simple
                ;;
            "standard")
                scenario_standard
                ;;
            "detailed")
                scenario_detailed
                ;;
            "full")
                scenario_full
                ;;
            "sapporo")
                scenario_sapporo
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

