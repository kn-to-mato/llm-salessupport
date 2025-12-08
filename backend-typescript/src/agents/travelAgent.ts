/**
 * 出張サポートエージェント
 *
 * Mastra Agent を使用した宣言的なエージェント定義:
 * - LLMが自律的にツールを選択・実行
 * - ツールの中でWorkflowを呼び出すことも可能
 *
 * ツール構成:
 * 1. policy_checker: 規程チェック
 * 2. transportation_search: 交通検索
 * 3. hotel_search: ホテル検索（日帰りならスキップ推奨）
 * 4. plan_generator: プラン生成
 */
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
1. **policy_checker**: 予算や規程について質問された場合に使用
2. **transportation_search**: 出発地・目的地・日付がわかったら使用
3. **hotel_search**: 宿泊が必要な場合（日帰りでない場合）に使用
4. **plan_generator**: 出発地・目的地・日程が揃ったら**必ず呼び出す**

## ツール選択のガイドライン
- **日帰りの場合** → hotel_search はスキップ
- **条件が不足している場合** → ツールを使わずにユーザーに質問
- **規程チェックを求められた場合** → policy_checker を使用
- **条件が揃ったら** → **必ず plan_generator を呼び出す**

## 重要な判断ポイント
1. ユーザーが「日帰り」「当日帰り」と言った場合は isDayTrip: true
2. 出発地・目的地・日程が揃っていなければ、まず質問する
3. 全条件が揃ったら **必ず plan_generator を呼び出してプランを提案**

## 絶対に守るべきルール
- **プランを提案する際は、必ず plan_generator ツールを使用してください。自分でプランをテキストで生成してはいけません。**
- 「お願いします」「それで進めて」などユーザーが確認した場合、条件が揃っていれば plan_generator を呼び出してください
- 会話の中で条件が揃ったら、すぐに plan_generator を呼び出してください

## 応答のガイドライン
- 日本語で丁寧に応答してください
- plan_generatorの結果をそのまま伝えてください
- 規程に関する注意事項があれば必ず伝えてください`;

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
