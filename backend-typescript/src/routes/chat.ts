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
        mlApp: process.env.DD_LLMOBS_ML_APP || "llm-salessupport",
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

            // エージェントを実行
            const agentResult = await travelAgent.generate(message + contextMessage, {
              maxSteps: 10,
            });

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

        const responseData = {
          response: result.text,
          session_id: sessionId,
          plans,
          conditions: session.conditions,
          _metadata: {
            version: APP_VERSION,
            framework: "typescript-mastra",
            duration_ms: Date.now() - startTime,
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

// レスポンスからプラン情報を抽出
function extractPlansFromResponse(text: string): Array<{
  name: string;
  transportation: string;
  hotel?: string;
  totalCost: number;
}> {
  const plans: Array<{
    name: string;
    transportation: string;
    hotel?: string;
    totalCost: number;
  }> = [];

  // プランA, B, C などのパターンを抽出
  const planMatches = text.matchAll(/プラン[A-C]|Plan\s*[A-C]/gi);
  for (const match of planMatches) {
    plans.push({
      name: match[0],
      transportation: "新幹線",
      totalCost: 0,
    });
  }

  return plans;
}
