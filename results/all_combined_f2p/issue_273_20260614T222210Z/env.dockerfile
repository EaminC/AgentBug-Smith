FROM python:3.11-slim AS builder

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tuzi/deepseek-v3.2"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tuzi/deepseek-v3.2"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi/deepseek-v3.2"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ git curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY . .

# Check for src layout or imports from src.
RUN if [ -d "src" ] || grep -r "^\s*from src\." . 2>/dev/null | head -1; then \
        echo "Detected src layout or src imports - skipping editable install." && export SKIP_EDITABLE=1; \
    else \
        echo "No src layout detected - will perform editable install." && export SKIP_EDITABLE=0; \
    fi

ENV PYTHONPATH=/app

RUN python -m pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt && \
    if [ "$SKIP_EDITABLE" = "0" ]; then pip install -e .; fi && \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Forge environment variables (required by test harness)
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co
ENV ANTHROPIC_AUTH_TOKEN=forge-key

RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

CMD ["/bin/bash"]