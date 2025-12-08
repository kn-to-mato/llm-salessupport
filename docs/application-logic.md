# アプリケーションロジック仕様

出張サポートAIのビジネスロジック詳細。Python版（LangChain）を基準とし、TypeScript版もこの仕様に従う。

---

## 1. アーキテクチャ概要

### 1.1 エージェント方式

```
┌─────────────────────────────────────────────────────────────┐
│  ユーザー入力                                                │
│  「東京から大阪に出張。12/9-10、新幹線希望、予算5万円」       │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  LLM (GPT-4o) - ツール選択                                  │
│  ユーザー入力を分析し、必要なツールを自律的に選択・実行       │
└─────────────────────────────────────────────────────────────┘
                              ↓
         ┌────────────┬────────────┬────────────┐
         ↓            ↓            ↓            ↓
    ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
    │ policy_ │ │ trans-  │ │ hotel_  │ │ plan_   │
    │ checker │ │ search  │ │ search  │ │generator│
    └─────────┘ └─────────┘ └─────────┘ └────┬────┘
                                             │
                              ┌──────────────┴──────────────┐
                              ↓                             ↓
                    ┌─────────────────┐         ┌─────────────────┐
                    │ transportation_ │         │ hotel_search    │
                    │ search (内部)   │         │ (内部)          │
                    └─────────────────┘         └─────────────────┘
```

**重要**: `plan_generator` は内部で `transportation_search` と `hotel_search` を呼び出す。

---

## 2. ツール仕様

### 2.1 policy_checker（規程チェック）

社内旅費規程に基づいて、出張条件の妥当性をチェック。

#### 入力パラメータ

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `is_domestic` | boolean | ○ | 国内出張かどうか |
| `transportation_type` | string | - | 交通手段（新幹線、飛行機等） |
| `total_budget` | number | - | 総予算（円） |
| `accommodation_budget_per_night` | number | - | 1泊あたりの宿泊予算（円） |
| `duration_days` | number | - | 出張日数 |

#### 出力

```json
{
  "is_compliant": true,
  "status": "適合",
  "messages": ["規程に適合しています"],
  "details": {
    "transportation_limit": 50000,
    "accommodation_limit_per_night": 15000,
    "daily_allowance": 2500
  }
}
```

#### 規程ルール（ハードコード）

| 項目 | 上限 |
|------|------|
| 宿泊費（一般） | 15,000円/泊 |
| 宿泊費（東京23区・大阪市内） | 18,000円/泊 |
| 日当 | 2,500円/日 |
| 交通手段 | 新幹線普通車 or ビジネスクラス以下 |

---

### 2.2 transportation_search（交通検索）

出発地・目的地間の交通手段を検索。

#### 入力パラメータ

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `departure` | string | ○ | 出発地（例：東京） |
| `destination` | string | ○ | 目的地（例：大阪） |
| `preferred_type` | string | - | 希望交通手段（新幹線、飛行機等） |
| `max_price` | number | - | 片道上限金額（円） |

#### 出力

```json
{
  "found": true,
  "departure": "東京",
  "destination": "大阪",
  "options": [
    {
      "type": "新幹線",
      "train_name": "のぞみ",
      "departure_station": "東京駅",
      "arrival_station": "新大阪駅",
      "schedules": [
        {"departure": "06:00", "arrival": "08:22", "price": 14720},
        {"departure": "08:00", "arrival": "10:22", "price": 14720}
      ],
      "duration_minutes": 142
    },
    {
      "type": "新幹線",
      "train_name": "ひかり",
      "departure_station": "東京駅",
      "arrival_station": "新大阪駅",
      "schedules": [
        {"departure": "06:33", "arrival": "09:23", "price": 14400}
      ],
      "duration_minutes": 170
    }
  ],
  "total_options": 2
}
```

#### モックデータ（主要路線）

| 出発 | 目的 | 交通手段 | 所要時間 | 料金 |
|-----|------|---------|---------|------|
| 東京 | 大阪 | のぞみ | 2時間22分 | 14,720円 |
| 東京 | 大阪 | ひかり | 2時間50分 | 14,400円 |
| 東京 | 大阪 | 飛行機 | 1時間10分 | 18,000〜25,000円 |
| 東京 | 名古屋 | のぞみ | 1時間40分 | 11,300円 |
| 東京 | 福岡 | 飛行機 | 2時間5分 | 28,000〜35,000円 |
| 東京 | 仙台 | はやぶさ | 1時間32分 | 11,410円 |

---

### 2.3 hotel_search（ホテル検索）

目的地周辺のホテルを検索。

#### 入力パラメータ

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `destination` | string | ○ | 宿泊地（例：大阪） |
| `nights` | number | - | 宿泊数（デフォルト: 1） |
| `max_price_per_night` | number | - | 1泊あたりの上限（円） |
| `preferred_area` | string | - | 希望エリア |

#### 出力

```json
{
  "found": true,
  "destination": "大阪",
  "nights": 1,
  "hotels": [
    {
      "name": "ドーミーイン心斎橋",
      "area": "心斎橋",
      "price_per_night": 12000,
      "rating": 4.2,
      "amenities": ["大浴場", "朝食無料", "Wi-Fi"]
    },
    {
      "name": "ダイワロイネットホテル大阪北浜",
      "area": "北浜",
      "price_per_night": 10800,
      "rating": 4.0,
      "amenities": ["Wi-Fi", "コインランドリー"]
    }
  ],
  "total_hotels": 2
}
```

#### モックデータ（主要都市）

| 都市 | ホテル名 | 料金/泊 | 評価 |
|-----|---------|--------|------|
| 大阪 | ドーミーイン心斎橋 | 12,000円 | 4.2 |
| 大阪 | ダイワロイネットホテル | 10,800円 | 4.0 |
| 大阪 | コンフォートホテル新大阪 | 8,500円 | 3.8 |
| 名古屋 | ダイワロイネットホテル名古屋 | 9,500円 | 4.1 |
| 福岡 | ドーミーイン博多 | 11,000円 | 4.3 |

---

### 2.4 plan_generator（プラン生成）★重要

交通・宿泊を組み合わせて出張プランを生成。**内部で他ツールを呼び出す。**

#### 入力パラメータ

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `departure_location` | string | ○ | 出発地 |
| `destination` | string | ○ | 目的地 |
| `depart_date` | string | ○ | 出発日（YYYY-MM-DD） |
| `return_date` | string | - | 帰着日（日帰りの場合は省略） |
| `budget` | number | - | 予算上限（円） |
| `preferred_transportation` | string | - | 希望交通手段 |

#### 内部処理フロー ★重要

```python
def _run(self, ...):
    # 1. 交通検索（内部呼び出し）
    trans_tool = TransportationSearchTool()
    trans_result = trans_tool._run(
        departure=departure_location,
        destination=destination,
        preferred_type=preferred_transportation,
    )
    transportation_options = trans_result.get("options", [])
    
    # 2. 宿泊数計算
    is_day_trip = return_date is None
    nights = calculate_nights(depart_date, return_date)
    
    # 3. ホテル検索（日帰りでない場合のみ、内部呼び出し）
    hotel_options = []
    if not is_day_trip and nights > 0:
        hotel_tool = HotelSearchTool()
        hotel_result = hotel_tool._run(
            destination=destination,
            nights=nights,
            max_price_per_night=15000,  # 規程上限
        )
        hotel_options = hotel_result.get("hotels", [])
    
    # 4. プラン生成（交通×ホテルの組み合わせ）
    plans = []
    for trans in transportation_options[:3]:
        if is_day_trip:
            # 日帰りプラン（ホテルなし）
            plan = create_day_trip_plan(trans, ...)
            plans.append(plan)
        else:
            # 宿泊プラン（交通×ホテル）
            for hotel in hotel_options[:2]:
                plan = create_stay_plan(trans, hotel, ...)
                plans.append(plan)
                if len(plans) >= 3:
                    break
    
    return {"success": True, "plans": plans, "total_plans": len(plans)}
```

#### 出力

```json
{
  "success": true,
  "plans": [
    {
      "plan_id": "uuid-1234",
      "label": "プランA",
      "summary": {
        "depart_date": "2024-12-09",
        "return_date": "2024-12-10",
        "destination": "大阪",
        "transportation": "新幹線（のぞみ）",
        "hotel": "ドーミーイン心斎橋 1泊",
        "estimated_total": 41440,
        "policy_status": "OK",
        "policy_note": null
      },
      "outbound_transportation": {
        "type": "新幹線",
        "train_name": "のぞみ",
        "departure_station": "東京駅",
        "arrival_station": "新大阪駅",
        "departure_time": "06:00",
        "arrival_time": "08:22",
        "price": 14720
      },
      "return_transportation": {
        "type": "新幹線",
        "train_name": "のぞみ",
        "departure_station": "新大阪駅",
        "arrival_station": "東京駅",
        "departure_time": "18:00",
        "price": 14720
      },
      "hotel": {
        "name": "ドーミーイン心斎橋",
        "area": "心斎橋",
        "price_per_night": 12000,
        "nights": 1,
        "total_price": 12000
      }
    }
  ],
  "total_plans": 3
}
```

---

## 3. LLMによるツール選択

### 3.1 システムプロンプト

```
あなたは営業担当者の出張計画をサポートするAIアシスタントです。

## あなたが使えるツール
1. policy_checker: 社内旅費規程をチェック
2. transportation_search: 交通手段を検索
3. hotel_search: ホテルを検索
4. plan_generator: 出張プランを生成（内部で交通・ホテル検索を行う）

## ツール選択のガイドライン
- 「規程」「予算」について言及 → policy_checker
- 出発地・目的地・日付がわかっている → plan_generator（推奨）
- 日帰りの場合 → hotel_search はスキップ
- 条件が不足 → ツールを使わずにユーザーに質問
```

### 3.2 期待される動作例

| ユーザー入力 | 呼ばれるツール | 理由 |
|-------------|--------------|------|
| 「東京から大阪に出張。12/9-10」 | `plan_generator` | 条件が揃っている |
| 「予算5万円で規程内か確認して」 | `policy_checker` | 規程チェック要求 |
| 「名古屋に日帰り出張」 | `plan_generator` | 日帰り（hotel_searchスキップ） |
| 「大阪のホテルを教えて」 | `hotel_search` | ホテル検索のみ |
| 「出張したい」 | なし（質問） | 条件不足 |

---

## 4. トレース構造

### 期待されるDatadogトレース

```
Agent: travel-support-agent (10s)
├── Workflow: agent_execution (9s)
│   ├── LLM: OpenAI.createChatCompletion (2s)
│   │   └── Output: TOOL CALL: plan_generator, policy_checker
│   ├── Tool: plan_generator (1s)
│   │   ├── Tool: transportation_search (0.1s)  ← 内部呼び出し
│   │   └── Tool: hotel_search (0.1s)           ← 内部呼び出し
│   ├── Tool: policy_checker (0.1s)
│   └── LLM: OpenAI.createChatCompletion (5s)
│       └── Output: 最終レスポンス
```

**ポイント**:
- `plan_generator` の下に `transportation_search`, `hotel_search` がネスト
- LLMのOutput MessageにTOOL CALLが表示される（自動計装）

---

## 5. 実装チェックリスト

### Python版 ✅

- [x] LangChain AgentExecutor使用
- [x] policy_checker: `@llmobs_tool` デコレータ
- [x] transportation_search: `@llmobs_tool` デコレータ
- [x] hotel_search: `@llmobs_tool` デコレータ
- [x] plan_generator: `@llmobs_tool` デコレータ + 内部でツール呼び出し
- [x] OpenAI自動計装（dd-trace）

### TypeScript版 ✅

- [x] Agent/Workflow手動計装
- [x] LLM手動計装（`kind: "llm"`）
- [x] policy_checker: Tool計装
- [x] transportation_search: Tool計装
- [x] hotel_search: Tool計装
- [x] **plan_generator: 内部でtransportation_search, hotel_searchを呼び出す**
- [x] トレースのネスト構造
- [x] 会話履歴の保持

