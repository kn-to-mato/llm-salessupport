#!/bin/bash
# Run two local frontends simultaneously with different ports.
#
# Example:
#   ./scripts/run-dual-frontend.sh \
#     --langchain-url http://kentomax-sales-support-alb-733711893.ap-northeast-1.elb.amazonaws.com \
#     --vertex-url https://kentomax-sales-support-backend-vertex-n4ow3sy4fq-an.a.run.app
#
# Defaults:
# - langchain-url: http://localhost:8000
# - vertex-url:    http://localhost:8001
# - ports:         5173 (langchain), 5174 (vertex)

set -euo pipefail

LANGCHAIN_URL="http://localhost:8000"
VERTEX_URL="http://localhost:8001"
LANGCHAIN_PORT="5173"
VERTEX_PORT="5174"

while [ $# -gt 0 ]; do
  case "$1" in
    --langchain-url)
      LANGCHAIN_URL="${2:?missing value}"
      shift 2
      ;;
    --vertex-url)
      VERTEX_URL="${2:?missing value}"
      shift 2
      ;;
    --langchain-port)
      LANGCHAIN_PORT="${2:?missing value}"
      shift 2
      ;;
    --vertex-port)
      VERTEX_PORT="${2:?missing value}"
      shift 2
      ;;
    -h|--help)
      echo "Usage: $0 [--langchain-url URL] [--vertex-url URL] [--langchain-port PORT] [--vertex-port PORT]"
      exit 0
      ;;
    *)
      echo "Unknown arg: $1"
      echo "Use --help"
      exit 1
      ;;
  esac
done

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo ""
echo "LangChain frontend:"
echo "  - Backend:  ${LANGCHAIN_URL}"
echo "  - Frontend: http://localhost:${LANGCHAIN_PORT}"
echo ""
echo "Vertex frontend:"
echo "  - Backend:  ${VERTEX_URL}"
echo "  - Frontend: http://localhost:${VERTEX_PORT}"
echo ""
echo "Starting... (Ctrl+C to stop both)"
echo ""

cleanup() {
  # kill all child processes in this process group
  kill 0 >/dev/null 2>&1 || true
}
trap cleanup INT TERM EXIT

(
  cd "${ROOT_DIR}/frontend"
  VITE_PORT="${LANGCHAIN_PORT}" \
  VITE_BACKEND_URL="${LANGCHAIN_URL}" \
  npm run dev
) &

(
  cd "${ROOT_DIR}/frontend"
  VITE_PORT="${VERTEX_PORT}" \
  VITE_BACKEND_URL="${VERTEX_URL}" \
  npm run dev
) &

wait
