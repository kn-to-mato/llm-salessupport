import { createTool } from "@mastra/core/tools";
import { z } from "zod";

// 社内規程データ（モック）
const COMPANY_POLICIES = {
  transportation: {
    domestic: {
      shinkansen: { green_car: false, max_distance_km: 1000 },
      airplane: { business_class: false, min_distance_km: 500 },
      express_bus: { allowed: true },
    },
    budget_per_day: 30000,
  },
  accommodation: {
    max_per_night: 15000,
    allowed_areas: ["都心部", "ビジネス街", "駅周辺"],
    advance_booking_days: 3,
  },
  meals: {
    breakfast: 1000,
    lunch: 1500,
    dinner: 3000,
  },
};

export const policyCheckerTool = createTool({
  id: "policy_checker",
  description: "社内旅費規程をチェックします。出張の交通手段、宿泊、予算が規程に準拠しているか確認します。",
  inputSchema: z.object({
    transportation_type: z.string().describe("交通手段の種類（新幹線、飛行機、バスなど）"),
    accommodation_budget: z.number().optional().describe("宿泊予算（1泊あたり）"),
    total_budget: z.number().optional().describe("出張全体の予算"),
    is_green_car: z.boolean().optional().describe("グリーン車利用の有無"),
    is_business_class: z.boolean().optional().describe("ビジネスクラス利用の有無"),
  }),
  outputSchema: z.object({
    compliant: z.boolean(),
    violations: z.array(z.string()),
    recommendations: z.array(z.string()),
    policy_summary: z.string(),
  }),
  execute: async ({ context }) => {
    const violations: string[] = [];
    const recommendations: string[] = [];

    // 交通手段チェック
    if (context.is_green_car && !COMPANY_POLICIES.transportation.domestic.shinkansen.green_car) {
      violations.push("グリーン車の利用は規程で認められていません");
      recommendations.push("普通車指定席をご利用ください");
    }

    if (context.is_business_class && !COMPANY_POLICIES.transportation.domestic.airplane.business_class) {
      violations.push("ビジネスクラスの利用は規程で認められていません");
      recommendations.push("エコノミークラスをご利用ください");
    }

    // 宿泊予算チェック
    if (context.accommodation_budget && context.accommodation_budget > COMPANY_POLICIES.accommodation.max_per_night) {
      violations.push(`宿泊費が上限（${COMPANY_POLICIES.accommodation.max_per_night}円/泊）を超えています`);
      recommendations.push(`${COMPANY_POLICIES.accommodation.max_per_night}円以下の宿泊施設をお選びください`);
    }

    const compliant = violations.length === 0;
    const policy_summary = compliant
      ? "すべての項目が社内規程に準拠しています"
      : `${violations.length}件の規程違反があります`;

    return {
      compliant,
      violations,
      recommendations,
      policy_summary,
    };
  },
});

