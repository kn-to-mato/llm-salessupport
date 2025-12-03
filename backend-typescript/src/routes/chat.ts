import { Hono } from "hono";
import { travelAgent } from "../agents";

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
  try {
    const body = await c.req.json();
    const { message, session_id } = body;

    if (!message) {
      return c.json({ error: "message is required" }, 400);
    }

    const sessionId = session_id || crypto.randomUUID();
    const session = getOrCreateSession(sessionId);

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

    // エージェントを実行
    const result = await travelAgent.generate(message + contextMessage, {
      maxSteps: 10,
    });

    // アシスタントの応答を履歴に追加
    session.chatHistory.push({ role: "assistant", content: result.text });

    // プラン情報を抽出（簡易実装）
    const plans = extractPlansFromResponse(result.text);

    return c.json({
      response: result.text,
      session_id: sessionId,
      plans,
      conditions: session.conditions,
    });
  } catch (error) {
    console.error("Chat error:", error);
    return c.json(
      {
        error: "Internal server error",
        details: error instanceof Error ? error.message : "Unknown error",
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
    });
  } catch (error) {
    console.error("Reset error:", error);
    return c.json({ error: "Internal server error" }, 500);
  }
});

// レスポンスからプラン情報を抽出（簡易実装）
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

