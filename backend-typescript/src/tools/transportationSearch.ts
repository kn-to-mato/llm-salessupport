import { createTool } from "@mastra/core/tools";
import { z } from "zod";

// 交通オプションの型定義
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

// モック交通データ生成
function generateMockTransportation(
  origin: string,
  destination: string,
  date: string,
  transportType?: string
): TransportationOption[] {
  const options: TransportationOption[] = [];

  // 新幹線オプション
  if (!transportType || transportType.includes("新幹線") || transportType === "train") {
    options.push(
      {
        type: "新幹線",
        name: "のぞみ1号",
        departure_time: "06:00",
        arrival_time: "08:22",
        duration: "2時間22分",
        price: 14720,
        departure_station: `${origin}駅`,
        arrival_station: `${destination}駅`,
      },
      {
        type: "新幹線",
        name: "ひかり501号",
        departure_time: "06:33",
        arrival_time: "09:23",
        duration: "2時間50分",
        price: 13870,
        departure_station: `${origin}駅`,
        arrival_station: `${destination}駅`,
      }
    );
  }

  // 飛行機オプション
  if (!transportType || transportType.includes("飛行機") || transportType === "airplane") {
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

  // バスオプション
  if (!transportType || transportType.includes("バス") || transportType === "bus") {
    options.push({
      type: "高速バス",
      name: "ドリーム号",
      departure_time: "23:00",
      arrival_time: "06:00",
      duration: "7時間",
      price: 5000,
      departure_station: `${origin}バスターミナル`,
      arrival_station: `${destination}バスターミナル`,
    });
  }

  return options;
}

export const transportationSearchTool = createTool({
  id: "transportation_search",
  description: "出発地から目的地への交通手段を検索します。新幹線、飛行機、バスなどの選択肢を提供します。",
  inputSchema: z.object({
    origin: z.string().describe("出発地（例：東京）"),
    destination: z.string().describe("目的地（例：大阪）"),
    date: z.string().describe("出発日（YYYY-MM-DD形式）"),
    preferred_transport: z.string().optional().describe("希望の交通手段（新幹線、飛行機、バスなど）"),
  }),
  outputSchema: z.object({
    options: z.array(
      z.object({
        type: z.string(),
        name: z.string(),
        departure_time: z.string(),
        arrival_time: z.string(),
        duration: z.string(),
        price: z.number(),
        departure_station: z.string(),
        arrival_station: z.string(),
      })
    ),
    search_summary: z.string(),
  }),
  execute: async ({ context }) => {
    const options = generateMockTransportation(
      context.origin,
      context.destination,
      context.date,
      context.preferred_transport
    );

    return {
      options,
      search_summary: `${context.origin}から${context.destination}への交通手段を${options.length}件見つけました`,
    };
  },
});

