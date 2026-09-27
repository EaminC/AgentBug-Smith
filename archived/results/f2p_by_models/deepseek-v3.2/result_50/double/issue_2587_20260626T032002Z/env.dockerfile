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

# Install system dependencies if needed (e.g., for building packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy entire repository (critical for external test script injection)
COPY . .

# Install dependencies using uv if uv.lock exists, else fallback to pip
# Based on repository evidence: pyproject.toml exists, uv is listed as dependency, and CI uses uv sync.
# The project uses hatchling build backend.
# CRITICAL: Install the project in editable mode unconditionally
RUN python -m pip install --upgrade pip wheel setuptools<=81.0.0 && \
    if [ -f uv.lock ]; then \
        pip install uv && \
        uv venv && \
        . .venv/bin/activate && uv sync --dev --all-extras; \
    else \
        if [ -f requirements.txt ]; then pip install -r requirements.txt; fi && \
        pip install -e .[tools,embeddings,agentops,fastembed,pdfplumber,pandas,openxyxl,mem0,docling,aisuite] 2>/dev/null || pip install -e .; \
    fi && \
    pip install pytest pytest-mock pytest-asyncio pytest-cov pytest-xdist pytest-timeout litellm mem0ai anyio

# Set PYTHONPATH to include src directory for proper imports without editable install
ENV PYTHONPATH=/app/src:$PYTHONPATH

# Preflight import check to ensure core modules can be loaded
RUN python -c "import crewai; import pytest; print('preflight ok')"

# Default command (test harness will override)
CMD ["/bin/bash"]