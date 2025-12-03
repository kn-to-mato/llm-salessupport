import { Agent } from "@mastra/core/agent";
import { openai } from "@ai-sdk/openai";
import {
  policyCheckerTool,
  transportationSearchTool,
  hotelSearchTool,
  planGeneratorTool,
} from "../tools";

const SYSTEM_PROMPT = `あなたは営業担当者の出張計画をサポートするAIアシスタントです。
ユーザーの出張希望を聞いて、最適なプランを提案します。

## あなたが使えるツール
1. policy_checker: 予算や規程について質問された場合に使用
2. transportation_search: 出発地・目的地・日付がわかったら使用
3. hotel_search: 宿泊が必要な場合（日帰りでない場合）に使用
4. plan_generator: 交通・宿泊情報が揃ったら使用

## ツール選択のガイドライン
- 日帰りの場合 → hotel_search はスキップ
- 条件が不足している場合 → ツールを使わずにユーザーに質問
- 規程チェックを求められた場合 → policy_checker を使用

## 応答のガイドライン
- 日本語で丁寧に応答してください
- プランを提案する際は、金額と所要時間を明記してください
- 複数の選択肢を提示し、それぞれの特徴を説明してください`;

export const travelAgent = new Agent({
  name: "travel-support-agent",
  instructions: SYSTEM_PROMPT,
  model: openai("gpt-4o"),
  tools: {
    policy_checker: policyCheckerTool,
    transportation_search: transportationSearchTool,
    hotel_search: hotelSearchTool,
    plan_generator: planGeneratorTool,
  },
});

