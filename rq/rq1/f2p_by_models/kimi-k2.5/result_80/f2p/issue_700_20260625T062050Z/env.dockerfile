FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tuzi-kimi-k2.5/kimi-k2.5"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tuzi-kimi-k2.5/kimi-k2.5"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi-kimi-k2.5/kimi-k2.5"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

WORKDIR /app

# Install system dependencies evidenced by CI workflows (universal-ctags) and git for repo operations
RUN apt-get update && apt-get install -y --no-install-recommends \
    universal-ctags \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy entire repository to ensure test scripts injected by orchestrator are preserved
COPY . .

# Install dependencies: requirements.txt exists per evidence, setup.py indicates setuptools project
# Combining install steps to avoid import errors and ensure test frameworks are present
RUN python -m pip install --upgrade pip wheel && \
    pip install -r requirements.txt && \
    pip install -e . && \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Preflight verification to fail fast on missing core components
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

CMD ["/bin/bash"]