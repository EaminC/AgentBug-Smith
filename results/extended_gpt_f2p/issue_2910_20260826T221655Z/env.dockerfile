FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tuzi-gpt-4.1-mini/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tuzi-gpt-4.1-mini/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi-gpt-4.1-mini/gpt-4.1-mini"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV OPENAI_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends git patch && rm -rf /var/lib/apt/lists/*

COPY . .

RUN set -eux; \
    python -m pip install --upgrade pip setuptools wheel packaging; \
    if [ -f "requirements.txt" ]; then \
        pip install -r requirements.txt; \
    fi; \
    pip install -e .; \
    pip install pytest pytest-mock pytest-asyncio pytest-cov

CMD ["/bin/bash"]