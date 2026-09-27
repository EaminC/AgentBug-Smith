FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="huggingface/tensorblock-gpt-4.1-mini"  # Corrected model provider prefix
ENV AI_TEMPERATURE="0.7"
ENV GITHUB_TOKEN="ghp_key"
ENV TAVILY_API_KEY="tvly-key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tensorblock/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="tensorblock/gpt-4.1-mini"
ENV OPENAI_API_KEY="forge-key"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
# --- end inject ---

WORKDIR /app

ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co \
    ANTHROPIC_AUTH_TOKEN=forge-key \
    FORGE_API_KEY=forge-key \
    FORGE_BASE_URL=https://api.forge.tensorblock.co/v1 \
    MODEL=huggingface/tensorblock-gpt-4.1-mini \  # Corrected model provider prefix
    AI_TEMPERATURE=0.7 \
    AI_MAX_TOKENS=1000 \
    AI_TOP_P=1 \
    AI_FREQUENCY_PENALTY=0 \
    AI_PRESENCE_PENALTY=0 \
    AI_STOP_SEQUENCES=[] \
    GITHUB_TOKEN=ghp_key \
    TAVILY_API_KEY=tvly-key \
    ANTHROPIC_MODEL=tensorblock/gpt-4.1-mini \
    ANTHROPIC_SMALL_FAST_MODEL=tensorblock/gpt-4.1-mini \
    PYTHONPATH=/app

COPY . .

RUN set -eux; \
    python -m pip install --upgrade pip setuptools wheel; \
    if [ -f "requirements.txt" ]; then pip install -r requirements.txt; fi; \
    pip install -e .; \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai; \
    python -c 'import pkg_resources, pytest; print("preflight ok")'

CMD ["/bin/bash"]