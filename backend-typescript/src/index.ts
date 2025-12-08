// dotenv を最初にインポート（環境変数を先に読み込む）
import "dotenv/config";

// トレーサーは dotenv の後、他のモジュールより前にインポート
import "./tracer";
import tracer, { APP_VERSION, llmobs } from "./tracer";

import { serve } from "@hono/node-server";
import { Hono } from "hono";
import { cors } from "hono/cors";
import { logger } from "hono/logger";
import { chatRouter } from "./routes";

const app = new Hono();

// ミドルウェア
app.use("*", logger());
app.use(
  "*",
  cors({
    origin: ["http://localhost:5173", "http://localhost:5174", "http://localhost:80"],
    allowMethods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allowHeaders: ["Content-Type", "Authorization"],
  })
);

// ヘルスチェック
app.get("/health", (c) => {
  return c.json({ 
    status: "healthy",
    version: APP_VERSION,
    framework: "typescript-mastra",
  });
});

// APIルート
app.route("/api/chat", chatRouter);

// サーバー起動
const port = parseInt(process.env.PORT || "3000", 10);

console.log(`🚀 Server starting on port ${port}...`);
console.log(`📍 Health check: http://localhost:${port}/health`);
console.log(`💬 Chat API: http://localhost:${port}/api/chat`);
console.log(`🔷 Version: ${APP_VERSION}`);
console.log(`📊 Datadog LLM Observability: ${process.env.DD_LLMOBS_ENABLED === "1" ? "enabled" : "disabled"}`);

serve({
  fetch: app.fetch,
  port,
});
