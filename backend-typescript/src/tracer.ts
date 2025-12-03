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

// トレーサー初期化（アプリケーション起動時に最初に呼び出す）
tracer.init({
  service: process.env.DD_SERVICE || "llm-salessupport-backend-typescript",
  env: process.env.DD_ENV || "dev",
  version: APP_VERSION,
  logInjection: true,
});

// LLM Observability 設定
tracer.use("openai", {
  // OpenAI 自動計装を有効化
});

// LLMObs インターフェースをエクスポート
export const llmobs = tracer.llmobs;

export default tracer;

