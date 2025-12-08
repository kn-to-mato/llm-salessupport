/**
 * チャット API ルート
 * 
 * Datadog LLM Observability SDK による計装:
 * - Python版と同じ構造でトレースを生成
 * - agent スパン → workflow スパン の階層構造
 */
import { Hono } from "hono";
import { travelAgent } from "../agents";
import { llmobs, APP_VERSION } from "../tracer";
// 検証用: Vercel AI SDK直接呼び出し
import { generateText, tool } from "ai";
import { openai } from "@ai-sdk/openai";
import { z } from "zod";

// セッションデータの型定義
interface SessionData {
  sessionId: string;
  chatHistory: Array<{ role: "user" | "assistant"; content: string }>;
  conditions: {
    origin?: string;
    destination?: string;
    departureDate?: string;
    returnDate?: string;
    budget?: number;
    preferredTransport?: string;
    isDayTrip?: boolean;
  };
}

// インメモリセッションストア（本番ではRedis等を使用）
const sessions = new Map<string, SessionData>();

// セッション取得または作成
function getOrCreateSession(sessionId: string): SessionData {
  if (!sessions.has(sessionId)) {
    sessions.set(sessionId, {
      sessionId,
      chatHistory: [],
      conditions: {},
    });
  }
  return sessions.get(sessionId)!;
}

export const chatRouter = new Hono();

// チャットエンドポイント
chatRouter.post("/", async (c) => {
  const startTime = Date.now();
  
  try {
    const body = await c.req.json();
    const { message, session_id } = body;

    if (!message) {
      return c.json({ error: "message is required" }, 400);
    }

    const sessionId = session_id || crypto.randomUUID();
    const session = getOrCreateSession(sessionId);

    // === LLMObs: Agent スパンを開始（Python版と同じ構造） ===
    const response = await llmobs.trace(
      {
        kind: "agent",
        name: "travel-support-agent",
        sessionId: sessionId,
        mlApp: process.env.DD_LLMOBS_ML_APP || "typescript-llm-salessupport",
      },
      async (agentSpan) => {
        // 入力データをアノテート
        llmobs.annotate(agentSpan, {
          inputData: {
            user_message: message,
            history_count: session.chatHistory.length,
            current_conditions: session.conditions,
            version: APP_VERSION,
          },
        });

        // チャット履歴にユーザーメッセージを追加
        session.chatHistory.push({ role: "user", content: message });

        // コンテキスト情報を構築
        const contextInfo = Object.entries(session.conditions)
          .filter(([_, v]) => v !== undefined)
          .map(([k, v]) => `${k}: ${v}`)
          .join(", ");

        const contextMessage = contextInfo
          ? `\n\n【現在の条件】${contextInfo}`
          : "";

        // === LLMObs: Workflow スパン（AgentExecutor相当） ===
        const result = await llmobs.trace(
          {
            kind: "workflow",
            name: "agent_execution",
          },
          async (workflowSpan) => {
            llmobs.annotate(workflowSpan, {
              inputData: {
                user_message: message,
                available_tools: ["policy_checker", "transportation_search", "hotel_search", "plan_generator"],
              },
            });

            // === LLMObs: LLM スパン（OpenAI API呼び出し） ===
            // Note: Mastra内部のLLM呼び出しは自動計装されないため手動計装
            const agentResult = await llmobs.trace(
              {
                kind: "llm",
                name: "openai.chat",
                modelName: "gpt-4o",
                modelProvider: "openai",
              },
              async (llmSpan) => {
                // 会話履歴を構築（過去の会話 + 現在のメッセージ）
                const historyMessages = session.chatHistory.slice(0, -1); // 最後のユーザーメッセージは除く（上で追加したばかり）
                
                // 会話履歴をテキストとして構築
                const historyText = historyMessages.length > 0
                  ? "【これまでの会話】\n" + historyMessages.map(m => 
                      `${m.role === "user" ? "ユーザー" : "アシスタント"}: ${m.content}`
                    ).join("\n") + "\n\n"
                  : "";

                const fullPrompt = historyText + "【現在のユーザーメッセージ】\n" + message + contextMessage;

                llmobs.annotate(llmSpan, {
                  inputData: [
                    { role: "user", content: fullPrompt },
                  ],
                });

                const result = await travelAgent.generate(fullPrompt, {
                  maxSteps: 10,
                });

                llmobs.annotate(llmSpan, {
                  outputData: {
                    content: result.text.substring(0, 500) + (result.text.length > 500 ? "..." : ""),
                  },
                });

                return result;
              }
            );

            llmobs.annotate(workflowSpan, {
              outputData: {
                response_length: agentResult.text.length,
                tools_available: ["policy_checker", "transportation_search", "hotel_search", "plan_generator"],
              },
            });

            return agentResult;
          }
        );

        // アシスタントの応答を履歴に追加
        session.chatHistory.push({ role: "assistant", content: result.text });

        // プラン情報を抽出
        const plans = extractPlansFromResponse(result.text);

        // フロントエンドの期待する形式に合わせる
        const responseData = {
          session_id: sessionId,
          messages: [
            {
              role: "assistant" as const,
              type: "text" as const,
              content: result.text,
            },
          ],
          plans,
          // 追加メタデータ（フロントエンドでは無視される）
          _metadata: {
            version: APP_VERSION,
            framework: "typescript-mastra",
            duration_ms: Date.now() - startTime,
            conditions: session.conditions,
          },
        };

        // 出力データをアノテート
        llmobs.annotate(agentSpan, {
          outputData: {
            response_length: result.text.length,
            plans_count: plans.length,
            duration_ms: Date.now() - startTime,
          },
        });

        return responseData;
      }
    );

    return c.json(response);
  } catch (error) {
    console.error("Chat error:", error);
    return c.json(
      {
        error: "Internal server error",
        details: error instanceof Error ? error.message : "Unknown error",
        _metadata: {
          version: APP_VERSION,
          framework: "typescript-mastra",
        },
      },
      500
    );
  }
});

// セッションリセット
chatRouter.post("/reset", async (c) => {
  try {
    const body = await c.req.json();
    const { session_id } = body;

    if (session_id && sessions.has(session_id)) {
      sessions.delete(session_id);
    }

    const newSessionId = crypto.randomUUID();
    getOrCreateSession(newSessionId);

    return c.json({
      message: "Session reset successfully",
      session_id: newSessionId,
      _metadata: {
        version: APP_VERSION,
        framework: "typescript-mastra",
      },
    });
  } catch (error) {
    console.error("Reset error:", error);
    return c.json({ error: "Internal server error" }, 500);
  }
});

// ============================================================
// 検証用: Vercel AI SDK直接呼び出し（Mastraを介さない）
// dd-traceの自動計装が効くか確認するためのエンドポイント
// ============================================================
chatRouter.post("/test-vercel-sdk", async (c) => {
  console.log("🧪 Testing Vercel AI SDK direct call (without Mastra)...");
  
  try {
    const body = await c.req.json();
    const { message } = body;

    // Vercel AI SDKのgenerateTextを直接呼び出し
    // dd-traceがこれをパッチしてtool_callsをキャプチャするはず
    const result = await generateText({
      model: openai("gpt-4o"),
      messages: [
        {
          role: "system",
          content: "あなたは出張計画をサポートするAIです。ユーザーの質問に簡潔に答えてください。",
        },
        {
          role: "user",
          content: message || "東京から大阪に出張したいです",
        },
      ],
      tools: {
        // テスト用のシンプルなツール定義（Zodスキーマ使用）
        get_weather: tool({
          description: "指定された都市の天気を取得します",
          parameters: z.object({
            city: z.string().describe("都市名"),
          }),
          execute: async ({ city }) => {
            return { city, weather: "晴れ", temperature: 20 };
          },
        }),
        search_hotel: tool({
          description: "指定された都市のホテルを検索します",
          parameters: z.object({
            city: z.string().describe("都市名"),
          }),
          execute: async ({ city }) => {
            return { city, hotels: ["ホテルA", "ホテルB"] };
          },
        }),
      },
      maxSteps: 5,
    });

    console.log("🧪 Vercel AI SDK result:", {
      text: result.text?.substring(0, 100),
      toolCalls: result.toolCalls,
      toolResults: result.toolResults,
    });

    return c.json({
      success: true,
      response: result.text,
      toolCalls: result.toolCalls,
      toolResults: result.toolResults,
      _test: "vercel-ai-sdk-direct",
    });
  } catch (error) {
    console.error("🧪 Test error:", error);
    return c.json({ error: String(error) }, 500);
  }
});

// フロントエンドが期待するTravelPlan形式
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
    policy_status: "OK" | "NG" | "注意";
    policy_note?: string;
  };
  outbound_transportation?: {
    type: string;
    departure_station: string;
    arrival_station: string;
    departure_time: string;
    arrival_time: string;
    price: number;
    train_name?: string;
  };
  hotel?: {
    name: string;
    area: string;
    price_per_night: number;
    nights: number;
    total_price: number;
    rating?: number;
  };
}

// レスポンスからプラン情報を抽出
// Note: 現時点ではテキストからの構造化抽出は複雑なため、空配列を返す
// プランカードの表示はPython版のように専用のplan_generatorツールで行う
function extractPlansFromResponse(_text: string): TravelPlan[] {
  // テキストからプランを正確に抽出するのは難しいため、
  // フロントエンドのクラッシュを防ぐために空配列を返す
  // TODO: plan_generatorツールの結果を直接使用するように改善
  return [];
}
