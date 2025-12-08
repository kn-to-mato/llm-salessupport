#!/bin/bash
# 会社名タグのテストスクリプト
# LLM Observabilityで会社名によるフィルタリングをテストするためのスクリプト

API_URL="${API_URL:-http://localhost:8000}"

# テスト用のメッセージリスト
MESSAGES=(
    "東京から大阪に出張したい"
    "名古屋に日帰りで行きたい"
    "福岡に来週出張予定"
    "規程を確認したい"
    "予算はいくらまで使える？"
    "新幹線で行きたい"
    "飛行機がいい"
    "2泊3日で出張したい"
    "ホテルはどこがいい？"
    "おすすめのプランは？"
)

echo "=============================================="
echo "  会社名タグ テストスクリプト"
echo "  API: $API_URL"
echo "=============================================="
echo ""

send_requests() {
    local company="$1"
    local count="$2"
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "会社名: $company"
    echo "リクエスト数: $count"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    local success=0
    local fail=0
    
    for ((i=1; i<=count; i++)); do
        # メッセージをランダムに選択
        local msg_index=$((RANDOM % ${#MESSAGES[@]}))
        local message="${MESSAGES[$msg_index]}"
        
        # リクエスト送信
        local response=$(curl -s -X POST "$API_URL/api/chat" \
            -H "Content-Type: application/json" \
            -d "{
                \"message\": \"$message\",
                \"user_id\": \"test-user-$i\",
                \"company_name\": \"$company\"
            }" 2>/dev/null)
        
        # レスポンスチェック
        if echo "$response" | grep -q "session_id"; then
            ((success++))
        else
            ((fail++))
        fi
        
        printf "\r  進捗: %d/%d (成功: %d, 失敗: %d)" "$i" "$count" "$success" "$fail"
        
        # レート制限回避のため少し待機
        sleep 0.3
    done
    
    echo ""
    echo "  結果: 成功=$success 失敗=$fail"
    echo ""
    
    return $success
}

TOTAL_SUCCESS=0

# A株式会社: 50リクエスト
send_requests "A株式会社" 50
TOTAL_SUCCESS=$((TOTAL_SUCCESS + $?))

# B Company: 23リクエスト
send_requests "B Company" 23
TOTAL_SUCCESS=$((TOTAL_SUCCESS + $?))

# 合同会社C.C.: 3リクエスト
send_requests "合同会社C.C." 3
TOTAL_SUCCESS=$((TOTAL_SUCCESS + $?))

echo "=============================================="
echo "  テスト完了"
echo "=============================================="
echo ""
echo "Datadogで以下のフィルターを試してください:"
echo "  @tags.company_name:\"A株式会社\""
echo "  @tags.company_name:\"B Company\""
echo "  @tags.company_name:\"合同会社C.C.\""
