FROM python:3.11-slim AS test_builder

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

# Pre-install system dependencies that may be required by Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Upgrade core packaging tools early
RUN python -m pip install --upgrade pip setuptools wheel

# Copy entire repository for externally-injected test scripts
COPY . .

# Detect src/ layout to decide editable install
RUN if [ -d "src" ] || grep -Rq "^\s*from src\.\|^\s*import src\." . 2>/dev/null; then \
        echo "src layout detected; skipping editable install, setting PYTHONPATH" && \
        export PYTHONPATH=/app && \
        pip install -r requirements.txt && \
        pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai; \
    else \
        echo "no src layout; performing editable install" && \
        pip install -r requirements.txt && \
        pip install -e . && \
        pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai; \
    fi

# Preflight import check to fail fast
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Set Forge environment variables
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co
ENV ANTHROPIC_AUTH_TOKEN=forge-key

CMD ["/bin/bash"]