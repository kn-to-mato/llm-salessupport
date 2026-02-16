# Backend (Vertex AI) Dockerfile
FROM --platform=linux/amd64 python:3.11-slim

WORKDIR /app

# Install system dependencies (keep minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Cloud Run uses $PORT (default 8080)
ENV PORT=8080

EXPOSE 8080

# Datadog LLM Observability auto-instrumentation:
# - We use ddtrace-run so ddtrace can patch supported libraries (Vertex AI SDK).
CMD ["sh", "-c", "ddtrace-run uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]

