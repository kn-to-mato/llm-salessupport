import { createTool } from "@mastra/core/tools";
import { z } from "zod";
import { llmobs } from "../tracer";

// === 内部で使用する検索関数（他ツールのロジックを再利用） ===

interface TransportationOption {
  type: string;
  name: string;
  departure_time: string;
  arrival_time: string;
  duration: string;
  price: number;
  departure_station: string;
  arrival_station: string;
}

interface HotelOption {
  name: string;
  area: string;
  price_per_night: number;
  rating: number;
  amenities: string[];
  distance_to_station: string;
}

// 交通手段を検索（内部関数）
function searchTransportation(
  origin: string,
  destination: string,
  preferredType?: string
): TransportationOption[] {
  const options: TransportationOption[] = [];

  if (!preferredType || preferredType.includes("新幹線")) {
    options.push(
      {
        type: "新幹線",
        name: "のぞみ1号",
        departure_time: "06:00",
        arrival_time: "08:22",
        duration: "2時間22分",
        price: 14720,
        departure_station: `${origin}駅`,
        arrival_station: `新${destination}駅`,
      },
      {
        type: "新幹線",
        name: "ひかり501号",
        departure_time: "06:33",
        arrival_time: "09:23",
        duration: "2時間50分",
        price: 13870,
        departure_station: `${origin}駅`,
        arrival_station: `新${destination}駅`,
      },
      {
        type: "新幹線",
        name: "こだま701号",
        departure_time: "06:00",
        arrival_time: "10:00",
        duration: "4時間",
        price: 11000,
        departure_station: `${origin}駅`,
        arrival_station: `新${destination}駅`,
      }
    );
  }

  if (!preferredType || preferredType.includes("飛行機")) {
    options.push({
      type: "飛行機",
      name: "ANA001",
      departure_time: "07:00",
      arrival_time: "08:15",
      duration: "1時間15分",
      price: 25000,
      departure_station: `${origin}空港`,
      arrival_station: `${destination}空港`,
    });
  }

  return options;
}

// ホテルを検索（内部関数）
function searchHotels(destination: string, maxPricePerNight?: number): HotelOption[] {
  const allHotels: HotelOption[] = [
    {
      name: "ドーミーイン心斎橋",
      area: `${destination}市内`,
      price_per_night: 12000,
      rating: 4.2,
      amenities: ["大浴場", "朝食付き", "Wi-Fi"],
      distance_to_station: "徒歩5分",
    },
    {
      name: "ダイワロイネットホテル大阪北浜",
      area: `${destination}市内`,
      price_per_night: 10800,
      rating: 4.0,
      amenities: ["Wi-Fi", "コインランドリー"],
      distance_to_station: "徒歩3分",
    },
    {
      name: "コンフォートホテル新大阪",
      area: `${destination}駅周辺`,
      price_per_night: 8500,
      rating: 3.8,
      amenities: ["朝食付き", "Wi-Fi"],
      distance_to_station: "徒歩1分",
    },
  ];

  if (maxPricePerNight) {
    return allHotels.filter((h) => h.price_per_night <= maxPricePerNight);
  }
  return allHotels;
}

// プランの型定義
interface TravelPlan {
  plan_id: string;
  label: string;
  summary: {
    depart_date: string;
    return_date: string;
    destination: string;
    transportation: string;
    hotel: string;
    estimated_total: number;
    policy_status: string;
    policy_note: string | null;
  };
  outbound_transportation: TransportationOption;
  return_transportation: TransportationOption;
  hotel: HotelOption | null;
}

export const planGeneratorTool = createTool({
  id: "plan_generator",
  description: `出発地・目的地・日程から最適な出張プランを複数パターン生成します。
内部で交通手段とホテルを検索し、予算や規程を考慮したプランを提案します。
日帰りの場合はreturn_dateを省略できます。`,
  inputSchema: z.object({
    departure_location: z.string().describe("出発地（例：東京）"),
    destination: z.string().describe("目的地（例：大阪）"),
    depart_date: z.string().describe("出発日（YYYY-MM-DD形式）"),
    return_date: z.string().optional().describe("帰着日（YYYY-MM-DD形式、日帰りの場合は省略可）"),
    budget: z.number().optional().describe("予算上限（円）"),
    preferred_transportation: z.string().optional().describe("希望交通手段（新幹線、飛行機など）"),
  }),
  outputSchema: z.object({
    success: z.boolean(),
    plans: z.array(z.any()),
    total_plans: z.number(),
  }),
  execute: async ({ context }) => {
    // === LLMObs: Tool スパンを手動計装 ===
    return await llmobs.trace(
      {
        kind: "tool",
        name: "plan_generator",
      },
      async (toolSpan) => {
        llmobs.annotate(toolSpan, {
          inputData: {
            departure_location: context.departure_location,
            destination: context.destination,
            depart_date: context.depart_date,
            return_date: context.return_date,
            budget: context.budget,
            preferred_transportation: context.preferred_transportation,
          },
        });

        const plans: TravelPlan[] = [];
        const planLabels = ["A", "B", "C", "D", "E"];
        let planCount = 0;

        // === LLMObs: 内部で transportation_search を呼び出し ===
        const transportationOptions = await llmobs.trace(
          {
            kind: "tool",
            name: "transportation_search",
          },
          async (transSpan) => {
            llmobs.annotate(transSpan, {
              inputData: {
                origin: context.departure_location,
                destination: context.destination,
                preferred_type: context.preferred_transportation,
              },
            });

            const options = searchTransportation(
              context.departure_location,
              context.destination,
              context.preferred_transportation
            );

            llmobs.annotate(transSpan, {
              outputData: {
                options_count: options.length,
              },
            });

            return options;
          }
        );

        // 宿泊数を計算
        const isDayTrip = !context.return_date;
        let nights = 0;

        if (!isDayTrip && context.return_date) {
          const depDate = new Date(context.depart_date);
          const retDate = new Date(context.return_date);
          nights = Math.ceil((retDate.getTime() - depDate.getTime()) / (1000 * 60 * 60 * 24));
        }

        // === LLMObs: 内部で hotel_search を呼び出し（日帰りでない場合） ===
        let hotelOptions: HotelOption[] = [];
        if (!isDayTrip && nights > 0) {
          hotelOptions = await llmobs.trace(
            {
              kind: "tool",
              name: "hotel_search",
            },
            async (hotelSpan) => {
              llmobs.annotate(hotelSpan, {
                inputData: {
                  destination: context.destination,
                  nights: nights,
                  max_price_per_night: 15000,
                },
              });

              const hotels = searchHotels(context.destination, 15000);

              llmobs.annotate(hotelSpan, {
                outputData: {
                  hotels_count: hotels.length,
                },
              });

              return hotels;
            }
          );
        }

        // 交通手段ごとにプランを生成
        if (isDayTrip) {
          // 日帰りプラン（ホテルなし）
          for (const trans of transportationOptions.slice(0, 3)) {
            if (planCount >= 3) break;

            const roundTripTrans = trans.price * 2;
            const total = roundTripTrans;

            let policyStatus = "OK";
            let policyNote: string | null = null;
            if (context.budget && total > context.budget) {
              policyStatus = "注意";
              policyNote = `予算 ${context.budget.toLocaleString()}円を${(total - context.budget).toLocaleString()}円超過しています`;
            }

            const plan: TravelPlan = {
              plan_id: crypto.randomUUID(),
              label: `プラン${planLabels[planCount]}`,
              summary: {
                depart_date: context.depart_date,
                return_date: context.depart_date, // 日帰りなので同日
                destination: context.destination,
                transportation: `${trans.type}（${trans.name}）`,
                hotel: "なし（日帰り）",
                estimated_total: total,
                policy_status: policyStatus,
                policy_note: policyNote,
              },
              outbound_transportation: trans,
              return_transportation: {
                ...trans,
                departure_station: trans.arrival_station,
                arrival_station: trans.departure_station,
                departure_time: "18:00",
                arrival_time: "",
              },
              hotel: null,
            };
            plans.push(plan);
            planCount++;
          }
        } else {
          // 宿泊ありプラン
          for (const trans of transportationOptions.slice(0, 3)) {
            for (const hotel of hotelOptions.slice(0, 2)) {
              if (planCount >= 3) break;

              const roundTripTrans = trans.price * 2;
              const hotelPrice = hotel.price_per_night * nights;
              const total = roundTripTrans + hotelPrice;

              let policyStatus = "OK";
              let policyNote: string | null = null;

              if (context.budget && total > context.budget) {
                policyStatus = "注意";
                policyNote = `予算 ${context.budget.toLocaleString()}円を${(total - context.budget).toLocaleString()}円超過しています`;
              }

              if (hotel.price_per_night > 15000) {
                policyStatus = "NG";
                policyNote = "宿泊費が規程上限（15,000円/泊）を超過しています";
              }

              const plan: TravelPlan = {
                plan_id: crypto.randomUUID(),
                label: `プラン${planLabels[planCount]}`,
                summary: {
                  depart_date: context.depart_date,
                  return_date: context.return_date!,
                  destination: context.destination,
                  transportation: `${trans.type}（${trans.name}）`,
                  hotel: `${hotel.name} ${nights}泊`,
                  estimated_total: total,
                  policy_status: policyStatus,
                  policy_note: policyNote,
                },
                outbound_transportation: trans,
                return_transportation: {
                  ...trans,
                  departure_station: trans.arrival_station,
                  arrival_station: trans.departure_station,
                  departure_time: "18:00",
                  arrival_time: "",
                },
                hotel: hotel,
              };
              plans.push(plan);
              planCount++;
            }
            if (planCount >= 3) break;
          }
        }

        // 予算内のプランを優先してソート
        if (context.budget) {
          plans.sort((a, b) => {
            const aOk = a.summary.policy_status === "OK" ? 0 : 1;
            const bOk = b.summary.policy_status === "OK" ? 0 : 1;
            if (aOk !== bOk) return aOk - bOk;
            return a.summary.estimated_total - b.summary.estimated_total;
          });
        }

        const result = {
          success: true,
          plans,
          total_plans: plans.length,
        };

        llmobs.annotate(toolSpan, {
          outputData: {
            success: true,
            total_plans: plans.length,
          },
        });

        return result;
      }
    );
  },
});
