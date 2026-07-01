FROM python:3.12-slim AS test_builder

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

WORKDIR /app

# Copy entire repository
COPY . .

# Install system dependencies if needed (for chromadb, tokenizers, onnxruntime, etc.)
# Based on pyproject.toml dependencies, we may need some system packages.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install project in editable mode (CRITICAL for multi-package layouts)
RUN pip install -e .

# Install test dependencies using uv (since project uses uv)
# Check for uv.lock (not present), fallback to uv sync --dev --all-extras as per .github/workflows/tests.yml
RUN python -m pip install --upgrade pip wheel && \
    if [ -f uv.lock ]; then \
        uv sync --dev --all-extras; \
    else \
        uv sync --dev --all-extras; \
    fi && \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Preflight import check
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

CMD ["/bin/bash"]