import { serve } from "@hono/node-server";
import { Hono } from "hono";
import { cors } from "hono/cors";
import { logger } from "hono/logger";
import { chatRouter } from "./routes";
import "dotenv/config";

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
  return c.json({ status: "healthy" });
});

// APIルート
app.route("/api/chat", chatRouter);

// サーバー起動
const port = parseInt(process.env.PORT || "3000", 10);

console.log(`🚀 Server starting on port ${port}...`);
console.log(`📍 Health check: http://localhost:${port}/health`);
console.log(`💬 Chat API: http://localhost:${port}/api/chat`);

serve({
  fetch: app.fetch,
  port,
});

