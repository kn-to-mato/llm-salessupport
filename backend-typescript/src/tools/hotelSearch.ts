import { createTool } from "@mastra/core/tools";
import { z } from "zod";
import { llmobs } from "../tracer";

// ホテルオプションの型定義
interface HotelOption {
  name: string;
  area: string;
  price_per_night: number;
  rating: number;
  amenities: string[];
  distance_to_station: string;
}

// モックホテルデータ生成
function generateMockHotels(destination: string, checkIn: string, checkOut: string): HotelOption[] {
  return [
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
    {
      name: "ホテルモントレ大阪",
      area: `${destination}市内`,
      price_per_night: 14500,
      rating: 4.5,
      amenities: ["レストラン", "フィットネス", "Wi-Fi"],
      distance_to_station: "徒歩7分",
    },
  ];
}

export const hotelSearchTool = createTool({
  id: "hotel_search",
  description: "目的地周辺のホテルを検索します。予算や設備に応じた宿泊施設を提案します。",
  inputSchema: z.object({
    destination: z.string().describe("宿泊地（例：大阪）"),
    check_in: z.string().describe("チェックイン日（YYYY-MM-DD形式）"),
    check_out: z.string().describe("チェックアウト日（YYYY-MM-DD形式）"),
    max_budget: z.number().optional().describe("1泊あたりの上限予算"),
  }),
  outputSchema: z.object({
    hotels: z.array(
      z.object({
        name: z.string(),
        area: z.string(),
        price_per_night: z.number(),
        rating: z.number(),
        amenities: z.array(z.string()),
        distance_to_station: z.string(),
      })
    ),
    search_summary: z.string(),
  }),
  execute: async ({ context }) => {
    // === LLMObs: Tool スパンを手動計装 ===
    return await llmobs.trace(
      {
        kind: "tool",
        name: "hotel_search",
      },
      async (toolSpan) => {
        llmobs.annotate(toolSpan, {
          inputData: {
            destination: context.destination,
            check_in: context.check_in,
            check_out: context.check_out,
            max_budget: context.max_budget,
          },
        });

        let hotels = generateMockHotels(context.destination, context.check_in, context.check_out);

        // 予算フィルタリング
        if (context.max_budget) {
          hotels = hotels.filter((h) => h.price_per_night <= context.max_budget!);
        }

        const result = {
          hotels,
          search_summary: `${context.destination}周辺のホテルを${hotels.length}件見つけました`,
        };

        llmobs.annotate(toolSpan, {
          outputData: {
            hotels_count: hotels.length,
            search_summary: result.search_summary,
          },
        });

        return result;
      }
    );
  },
});
