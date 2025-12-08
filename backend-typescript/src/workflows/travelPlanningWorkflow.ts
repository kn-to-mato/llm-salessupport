/**
 * 出張計画ワークフロー
 *
 * Mastra Workflow を使用した明示的なステップ制御:
 * - Step 1: 条件抽出
 * - Step 2: 交通検索（条件が揃っている場合）
 * - Step 3: ホテル検索（日帰りでない場合のみ）
 * - Step 4: プラン生成
 */
import { createWorkflow, createStep } from "@mastra/core/workflows";
import { z } from "zod";

// ============================================================
// 入出力スキーマ定義
// ============================================================

const TravelConditionsSchema = z.object({
  origin: z.string().optional().describe("出発地"),
  destination: z.string().optional().describe("目的地"),
  departDate: z.string().optional().describe("出発日 YYYY-MM-DD"),
  returnDate: z.string().optional().describe("帰着日 YYYY-MM-DD（日帰りならnull）"),
  budget: z.number().optional().describe("予算上限"),
  preferredTransport: z.string().optional().describe("希望交通手段"),
  isDayTrip: z.boolean().default(false).describe("日帰りかどうか"),
});

const TransportOptionSchema = z.object({
  type: z.string(),
  name: z.string(),
  departureTime: z.string(),
  arrivalTime: z.string(),
  duration: z.string(),
  price: z.number(),
  departureStation: z.string(),
  arrivalStation: z.string(),
});

const HotelOptionSchema = z.object({
  name: z.string(),
  area: z.string(),
  pricePerNight: z.number(),
  rating: z.number(),
  amenities: z.array(z.string()),
  distanceToStation: z.string(),
});

const TravelPlanSchema = z.object({
  planId: z.string(),
  label: z.string(),
  summary: z.object({
    departDate: z.string(),
    returnDate: z.string(),
    destination: z.string(),
    transportation: z.string(),
    hotel: z.string(),
    estimatedTotal: z.number(),
    policyStatus: z.string(),
    policyNote: z.string().nullable(),
  }),
  outboundTransportation: TransportOptionSchema.nullable(),
  returnTransportation: TransportOptionSchema.nullable(),
  hotel: HotelOptionSchema.nullable(),
});

// ============================================================
// Step 1: 条件抽出
// ============================================================
const extractConditionsStep = createStep({
  id: "extract-conditions",
  inputSchema: z.object({
    userMessage: z.string(),
    currentConditions: TravelConditionsSchema.optional(),
  }),
  outputSchema: TravelConditionsSchema,
  execute: async ({ inputData }) => {
    const { userMessage, currentConditions } = inputData;

    // 簡易的な条件抽出（本番ではLLMを使用）
    const extracted: z.infer<typeof TravelConditionsSchema> = {
      origin: currentConditions?.origin,
      destination: currentConditions?.destination,
      departDate: currentConditions?.departDate,
      returnDate: currentConditions?.returnDate,
      budget: currentConditions?.budget,
      preferredTransport: currentConditions?.preferredTransport,
      isDayTrip: currentConditions?.isDayTrip ?? false,
    };

    // パターンマッチで条件を抽出
    const originMatch = userMessage.match(/(.+?)から/);
    if (originMatch) extracted.origin = originMatch[1].trim();

    const destMatch = userMessage.match(/から(.+?)に/);
    if (destMatch) extracted.destination = destMatch[1].trim();

    const dateMatch = userMessage.match(/(\d{1,2})月(\d{1,2})日/g);
    if (dateMatch && dateMatch.length >= 1) {
      const year = new Date().getFullYear();
      const firstDate = dateMatch[0].match(/(\d{1,2})月(\d{1,2})日/);
      if (firstDate) {
        extracted.departDate = `${year}-${firstDate[1].padStart(2, "0")}-${firstDate[2].padStart(2, "0")}`;
      }
      if (dateMatch.length >= 2) {
        const secondDate = dateMatch[1].match(/(\d{1,2})月(\d{1,2})日/);
        if (secondDate) {
          extracted.returnDate = `${year}-${secondDate[1].padStart(2, "0")}-${secondDate[2].padStart(2, "0")}`;
        }
      }
    }

    // 日帰り判定
    if (userMessage.includes("日帰り") || userMessage.includes("当日")) {
      extracted.isDayTrip = true;
      extracted.returnDate = extracted.departDate;
    }

    // 交通手段
    if (userMessage.includes("新幹線")) extracted.preferredTransport = "新幹線";
    if (userMessage.includes("飛行機")) extracted.preferredTransport = "飛行機";
    if (userMessage.includes("バス")) extracted.preferredTransport = "バス";

    // 予算
    const budgetMatch = userMessage.match(/(\d+)万円/);
    if (budgetMatch) extracted.budget = parseInt(budgetMatch[1]) * 10000;

    return extracted;
  },
});

// ============================================================
// Step 2: 交通検索
// ============================================================
const searchTransportationStep = createStep({
  id: "search-transportation",
  inputSchema: TravelConditionsSchema,
  outputSchema: z.object({
    options: z.array(TransportOptionSchema),
    searchSummary: z.string(),
  }),
  execute: async ({ inputData }) => {
    const { origin, destination, preferredTransport } = inputData;

    if (!origin || !destination) {
      return { options: [], searchSummary: "出発地または目的地が不明です" };
    }

    // モックデータ生成
    const options: z.infer<typeof TransportOptionSchema>[] = [];

    if (!preferredTransport || preferredTransport.includes("新幹線")) {
      options.push(
        {
          type: "新幹線",
          name: "のぞみ1号",
          departureTime: "06:00",
          arrivalTime: "08:22",
          duration: "2時間22分",
          price: 14720,
          departureStation: `${origin}駅`,
          arrivalStation: `新${destination}駅`,
        },
        {
          type: "新幹線",
          name: "ひかり501号",
          departureTime: "06:33",
          arrivalTime: "09:23",
          duration: "2時間50分",
          price: 13870,
          departureStation: `${origin}駅`,
          arrivalStation: `新${destination}駅`,
        },
        {
          type: "新幹線",
          name: "こだま701号",
          departureTime: "06:00",
          arrivalTime: "10:00",
          duration: "4時間",
          price: 11000,
          departureStation: `${origin}駅`,
          arrivalStation: `新${destination}駅`,
        }
      );
    }

    if (!preferredTransport || preferredTransport.includes("飛行機")) {
      options.push({
        type: "飛行機",
        name: "ANA001",
        departureTime: "07:00",
        arrivalTime: "08:15",
        duration: "1時間15分",
        price: 25000,
        departureStation: `${origin}空港`,
        arrivalStation: `${destination}空港`,
      });
    }

    return {
      options,
      searchSummary: `${origin}から${destination}への交通手段を${options.length}件見つけました`,
    };
  },
});

// ============================================================
// Step 3: ホテル検索（日帰りでない場合のみ実行）
// ============================================================
const searchHotelsStep = createStep({
  id: "search-hotels",
  inputSchema: z.object({
    conditions: TravelConditionsSchema,
    transportationResult: z.object({
      options: z.array(TransportOptionSchema),
      searchSummary: z.string(),
    }),
  }),
  outputSchema: z.object({
    hotels: z.array(HotelOptionSchema),
    searchSummary: z.string(),
    skipped: z.boolean(),
  }),
  execute: async ({ inputData }) => {
    const { conditions } = inputData;

    // 日帰りの場合はスキップ
    if (conditions.isDayTrip) {
      return {
        hotels: [],
        searchSummary: "日帰りのためホテル検索をスキップしました",
        skipped: true,
      };
    }

    if (!conditions.destination) {
      return {
        hotels: [],
        searchSummary: "目的地が不明です",
        skipped: false,
      };
    }

    // モックホテルデータ
    const hotels: z.infer<typeof HotelOptionSchema>[] = [
      {
        name: "ドーミーイン心斎橋",
        area: `${conditions.destination}市内`,
        pricePerNight: 12000,
        rating: 4.2,
        amenities: ["大浴場", "朝食付き", "Wi-Fi"],
        distanceToStation: "徒歩5分",
      },
      {
        name: "ダイワロイネットホテル大阪北浜",
        area: `${conditions.destination}市内`,
        pricePerNight: 10800,
        rating: 4.0,
        amenities: ["Wi-Fi", "コインランドリー"],
        distanceToStation: "徒歩3分",
      },
      {
        name: "コンフォートホテル新大阪",
        area: `${conditions.destination}駅周辺`,
        pricePerNight: 8500,
        rating: 3.8,
        amenities: ["朝食付き", "Wi-Fi"],
        distanceToStation: "徒歩1分",
      },
    ];

    return {
      hotels,
      searchSummary: `${conditions.destination}周辺のホテルを${hotels.length}件見つけました`,
      skipped: false,
    };
  },
});

// ============================================================
// Step 4: プラン生成
// ============================================================
const generatePlansStep = createStep({
  id: "generate-plans",
  inputSchema: z.object({
    conditions: TravelConditionsSchema,
    transportationResult: z.object({
      options: z.array(TransportOptionSchema),
      searchSummary: z.string(),
    }),
    hotelResult: z.object({
      hotels: z.array(HotelOptionSchema),
      searchSummary: z.string(),
      skipped: z.boolean(),
    }),
  }),
  outputSchema: z.object({
    plans: z.array(TravelPlanSchema),
    totalPlans: z.number(),
  }),
  execute: async ({ inputData }) => {
    const { conditions, transportationResult, hotelResult } = inputData;
    const plans: z.infer<typeof TravelPlanSchema>[] = [];
    const planLabels = ["A", "B", "C"];
    let planCount = 0;

    // 宿泊数を計算
    let nights = 0;
    if (conditions.departDate && conditions.returnDate && !conditions.isDayTrip) {
      const dep = new Date(conditions.departDate);
      const ret = new Date(conditions.returnDate);
      nights = Math.ceil((ret.getTime() - dep.getTime()) / (1000 * 60 * 60 * 24));
    }

    if (conditions.isDayTrip) {
      // 日帰りプラン
      for (const trans of transportationResult.options.slice(0, 3)) {
        if (planCount >= 3) break;

        const total = trans.price * 2;
        let policyStatus = "OK";
        let policyNote: string | null = null;

        if (conditions.budget && total > conditions.budget) {
          policyStatus = "注意";
          policyNote = `予算 ${conditions.budget.toLocaleString()}円を${(total - conditions.budget).toLocaleString()}円超過`;
        }

        plans.push({
          planId: crypto.randomUUID(),
          label: `プラン${planLabels[planCount]}`,
          summary: {
            departDate: conditions.departDate || "",
            returnDate: conditions.departDate || "",
            destination: conditions.destination || "",
            transportation: `${trans.type}（${trans.name}）`,
            hotel: "なし（日帰り）",
            estimatedTotal: total,
            policyStatus,
            policyNote,
          },
          outboundTransportation: trans,
          returnTransportation: {
            ...trans,
            departureStation: trans.arrivalStation,
            arrivalStation: trans.departureStation,
            departureTime: "18:00",
            arrivalTime: "",
          },
          hotel: null,
        });
        planCount++;
      }
    } else {
      // 宿泊ありプラン
      for (const trans of transportationResult.options.slice(0, 3)) {
        for (const hotel of hotelResult.hotels.slice(0, 2)) {
          if (planCount >= 3) break;

          const roundTripTrans = trans.price * 2;
          const hotelPrice = hotel.pricePerNight * nights;
          const total = roundTripTrans + hotelPrice;

          let policyStatus = "OK";
          let policyNote: string | null = null;

          if (conditions.budget && total > conditions.budget) {
            policyStatus = "注意";
            policyNote = `予算 ${conditions.budget.toLocaleString()}円を${(total - conditions.budget).toLocaleString()}円超過`;
          }

          if (hotel.pricePerNight > 15000) {
            policyStatus = "NG";
            policyNote = "宿泊費が規程上限（15,000円/泊）を超過";
          }

          plans.push({
            planId: crypto.randomUUID(),
            label: `プラン${planLabels[planCount]}`,
            summary: {
              departDate: conditions.departDate || "",
              returnDate: conditions.returnDate || "",
              destination: conditions.destination || "",
              transportation: `${trans.type}（${trans.name}）`,
              hotel: `${hotel.name} ${nights}泊`,
              estimatedTotal: total,
              policyStatus,
              policyNote,
            },
            outboundTransportation: trans,
            returnTransportation: {
              ...trans,
              departureStation: trans.arrivalStation,
              arrivalStation: trans.departureStation,
              departureTime: "18:00",
              arrivalTime: "",
            },
            hotel: {
              ...hotel,
            },
          });
          planCount++;
        }
        if (planCount >= 3) break;
      }
    }

    return {
      plans,
      totalPlans: plans.length,
    };
  },
});

// ============================================================
// ワークフロー定義
// ============================================================
export const travelPlanningWorkflow = createWorkflow({
  id: "travel-planning-workflow",
  inputSchema: z.object({
    userMessage: z.string(),
    currentConditions: TravelConditionsSchema.optional(),
  }),
  outputSchema: z.object({
    conditions: TravelConditionsSchema,
    plans: z.array(TravelPlanSchema),
    totalPlans: z.number(),
    requiresMoreInfo: z.boolean(),
    missingFields: z.array(z.string()),
  }),
})
  .then(extractConditionsStep)
  .then(searchTransportationStep, {
    when: {
      "extract-conditions": {
        origin: { $ne: undefined },
        destination: { $ne: undefined },
      },
    },
  })
  .then(searchHotelsStep, {
    variables: {
      conditions: { step: extractConditionsStep, path: "." },
      transportationResult: { step: searchTransportationStep, path: "." },
    },
    when: {
      "extract-conditions": {
        isDayTrip: { $ne: true },
      },
    },
  })
  .then(generatePlansStep, {
    variables: {
      conditions: { step: extractConditionsStep, path: "." },
      transportationResult: { step: searchTransportationStep, path: "." },
      hotelResult: { step: searchHotelsStep, path: "." },
    },
  })
  .commit();

// ワークフロー実行のヘルパー関数
export async function runTravelPlanningWorkflow(input: {
  userMessage: string;
  currentConditions?: z.infer<typeof TravelConditionsSchema>;
}) {
  const result = await travelPlanningWorkflow.execute({
    inputData: input,
  });

  return result;
}

