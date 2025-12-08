/**
 * Datadog トレーサー初期化
 * 
 * LLM Observability SDK を使用したカスタム計装
 * Python版と同じ構造でトレースを生成
 * 
 * 参考: https://docs.datadoghq.com/llm_observability/instrumentation/sdk?tab=nodejs
 */
import tracer from "dd-trace";

// バージョンタグ（Python版との区別用）
export const APP_VERSION = "typescript-mastra-v1";

// LLMObs が有効かどうか
const llmobsEnabled = process.env.DD_LLMOBS_ENABLED === "1";

// トレーサー初期化（アプリケーション起動時に最初に呼び出す）
tracer.init({
  service: process.env.DD_SERVICE || "typescript-llm-salessupport",
  env: process.env.DD_ENV || "dev",
  version: APP_VERSION,
  logInjection: true,
  // LLM Observability 設定
  llmobs: llmobsEnabled ? {
    mlApp: process.env.DD_LLMOBS_ML_APP || "typescript-llm-salessupport",
    agentlessEnabled: process.env.DD_LLMOBS_AGENTLESS_ENABLED === "1",
    apiKey: process.env.DD_API_KEY,  // APIキーを明示的に渡す
  } : undefined,
});

// LLM 自動計装を明示的に有効化
// https://docs.datadoghq.com/ja/llm_observability/instrumentation/auto_instrumentation?tab=nodejs
tracer.use("openai", { enabled: true });   // OpenAI SDK
tracer.use("ai", { enabled: true });       // Vercel AI SDK

console.log("🔷 LLM integrations enabled: openai, ai (Vercel AI SDK)");

// LLMObs インターフェースをエクスポート
export const llmobs = tracer.llmobs;

// デバッグログ
if (llmobsEnabled) {
  console.log("🔷 LLMObs config:", {
    mlApp: process.env.DD_LLMOBS_ML_APP,
    agentlessEnabled: process.env.DD_LLMOBS_AGENTLESS_ENABLED === "1",
    apiKeySet: !!process.env.DD_API_KEY,
  });
}

export default tracer;

