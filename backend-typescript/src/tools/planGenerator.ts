import { createTool } from "@mastra/core/tools";
import { z } from "zod";

// プランの型定義
interface TravelPlan {
  plan_id: string;
  name: string;
  transportation: {
    outbound: {
      type: string;
      name: string;
      departure: string;
      arrival: string;
      price: number;
    };
    return: {
      type: string;
      name: string;
      departure: string;
      arrival: string;
      price: number;
    };
  };
  hotel?: {
    name: string;
    nights: number;
    price_per_night: number;
  };
  total_cost: number;
  recommendation_reason: string;
}

export const planGeneratorTool = createTool({
  id: "plan_generator",
  description: "交通手段とホテル情報を組み合わせて、最適な出張プランを生成します。",
  inputSchema: z.object({
    origin: z.string().describe("出発地"),
    destination: z.string().describe("目的地"),
    departure_date: z.string().describe("出発日"),
    return_date: z.string().describe("帰着日"),
    preferred_transport: z.string().optional().describe("希望の交通手段"),
    max_budget: z.number().optional().describe("予算上限"),
    is_day_trip: z.boolean().optional().describe("日帰りかどうか"),
  }),
  outputSchema: z.object({
    plans: z.array(
      z.object({
        plan_id: z.string(),
        name: z.string(),
        transportation: z.object({
          outbound: z.object({
            type: z.string(),
            name: z.string(),
            departure: z.string(),
            arrival: z.string(),
            price: z.number(),
          }),
          return: z.object({
            type: z.string(),
            name: z.string(),
            departure: z.string(),
            arrival: z.string(),
            price: z.number(),
          }),
        }),
        hotel: z
          .object({
            name: z.string(),
            nights: z.number(),
            price_per_night: z.number(),
          })
          .optional(),
        total_cost: z.number(),
        recommendation_reason: z.string(),
      })
    ),
    summary: z.string(),
  }),
  execute: async ({ context }) => {
    const plans: TravelPlan[] = [];
    const isDayTrip = context.is_day_trip || context.departure_date === context.return_date;

    // プランA: のぞみ + ドーミーイン
    const planA: TravelPlan = {
      plan_id: "plan_a",
      name: "プランA（おすすめ）",
      transportation: {
        outbound: {
          type: "新幹線",
          name: "のぞみ1号",
          departure: `${context.origin}駅 06:00発`,
          arrival: `新${context.destination}駅 08:22着`,
          price: 14720,
        },
        return: {
          type: "新幹線",
          name: "のぞみ50号",
          departure: `新${context.destination}駅 18:00発`,
          arrival: `${context.origin}駅 20:22着`,
          price: 14720,
        },
      },
      total_cost: 29440,
      recommendation_reason: "最速の移動で効率的なスケジュール",
    };

    if (!isDayTrip) {
      planA.hotel = {
        name: "ドーミーイン心斎橋",
        nights: 1,
        price_per_night: 12000,
      };
      planA.total_cost += 12000;
    }

    plans.push(planA);

    // プランB: ひかり + ダイワロイネット
    const planB: TravelPlan = {
      plan_id: "plan_b",
      name: "プランB（コスパ重視）",
      transportation: {
        outbound: {
          type: "新幹線",
          name: "ひかり501号",
          departure: `${context.origin}駅 06:33発`,
          arrival: `新${context.destination}駅 09:23着`,
          price: 13870,
        },
        return: {
          type: "新幹線",
          name: "ひかり540号",
          departure: `新${context.destination}駅 17:30発`,
          arrival: `${context.origin}駅 20:20着`,
          price: 13870,
        },
      },
      total_cost: 27740,
      recommendation_reason: "少し時間はかかるが経済的",
    };

    if (!isDayTrip) {
      planB.hotel = {
        name: "ダイワロイネットホテル大阪北浜",
        nights: 1,
        price_per_night: 10800,
      };
      planB.total_cost += 10800;
    }

    plans.push(planB);

    // プランC: 最安（日帰りのみ）
    if (isDayTrip) {
      plans.push({
        plan_id: "plan_c",
        name: "プランC（最安）",
        transportation: {
          outbound: {
            type: "新幹線",
            name: "こだま701号",
            departure: `${context.origin}駅 06:00発`,
            arrival: `新${context.destination}駅 10:00着`,
            price: 11000,
          },
          return: {
            type: "新幹線",
            name: "こだま740号",
            departure: `新${context.destination}駅 16:00発`,
            arrival: `${context.origin}駅 20:00着`,
            price: 11000,
          },
        },
        total_cost: 22000,
        recommendation_reason: "最も経済的な選択肢",
      });
    }

    // 予算フィルタリング
    const filteredPlans = context.max_budget
      ? plans.filter((p) => p.total_cost <= context.max_budget!)
      : plans;

    return {
      plans: filteredPlans,
      summary: `${filteredPlans.length}件のプランを生成しました。${isDayTrip ? "（日帰り）" : ""}`,
    };
  },
});

