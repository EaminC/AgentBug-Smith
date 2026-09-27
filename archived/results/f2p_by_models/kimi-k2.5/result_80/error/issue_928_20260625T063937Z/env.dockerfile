FROM python:3.11-slim

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

# Install system dependencies: git, tkinter, build tools, and clean up
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    python3-tk \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY . .

# Install dependencies with robust conditional logic and unconditional editable install
RUN python -m pip install --upgrade pip wheel && \
    if [ -f requirements.txt ]; then \
        pip install -r requirements.txt; \
    fi && \
    if [ -f pyproject.toml ] && [ -f poetry.lock ]; then \
        pip install poetry && \
        poetry config virtualenvs.create false && \
        poetry install --no-interaction --no-ansi; \
    fi && \
    pip install -e . && \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout

# Configure PYTHONPATH for potential monorepo or src-layout structures
ENV PYTHONPATH=/app:/app/src:$PYTHONPATH

# Preflight verification to ensure core tooling and agentscope are importable
RUN python -c "import agentscope; print('agentscope imported successfully')" && \
    python -c "from agentscope.formatter import DashScopeChatFormatter; print('DashScopeChatFormatter imported successfully')" && \
    python -c "import pytest; print('pytest imported successfully')"

CMD ["/bin/bash"]