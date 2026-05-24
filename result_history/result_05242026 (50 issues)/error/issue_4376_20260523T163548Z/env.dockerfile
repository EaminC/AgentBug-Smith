# syntax=docker/dockerfile:1

FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tensorblock/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV GITHUB_TOKEN="ghp_key"
ENV TAVILY_API_KEY="tvly-key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tensorblock/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="tensorblock/gpt-4.1-mini"
ENV OPENAI_API_KEY="forge-key"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
# --- end inject ---

ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1" \
    OPENAI_API_KEY="forge-key" \
    ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co" \
    ANTHROPIC_AUTH_TOKEN="forge-key" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY . .

RUN set -eux; \
    apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        python3-dev \
        libffi-dev \
        libxml2-dev \
        libxslt1-dev \
        build-essential \
        libyaml-dev \
        libyaml-0-2 \
    && rm -rf /var/lib/apt/lists/*; \
    # Pin setuptools to 65.5.0 to avoid PyYAML build errors on Python 3.12
    pip install --no-cache-dir --upgrade pip setuptools==65.5.0 wheel cython; \
    if [ -f requirements.txt ]; then \
        pip install --no-cache-dir -r requirements.txt || pip install --no-cache-dir --pre -r requirements.txt; \
    fi; \
    pip install --no-cache-dir -e .; \
    pip install --no-cache-dir pytest pytest-mock pytest-asyncio pytest-cov anyio litellm pytest-xdist pytest-timeout mem0ai

RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

CMD ["/bin/bash"]