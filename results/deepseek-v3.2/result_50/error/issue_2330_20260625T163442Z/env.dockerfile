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

# Install system dependencies needed for some Python packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ curl && \
    rm -rf /var/lib/apt/lists/*

# Copy entire repository (required for external test script injection)
COPY . .

# Pre-flight: check for existence of key dependency files
RUN [ -f pyproject.toml ] || { echo "pyproject.toml not found"; exit 1; }

# Install dependencies using uv (as indicated by pyproject.toml and .github/workflows)
# Since uv.lock does not exist in the file list, we use uv sync with dev and extras.
RUN python -m pip install --upgrade pip wheel && \
    pip install uv && \
    uv sync --dev --all-extras

# CRITICAL: Install the local package in editable mode
RUN pip install -e .

# The repository uses src/ layout (src/crewai). To avoid duplicate module loading,
# we set PYTHONPATH to include /app/src.
ENV PYTHONPATH=/app/src:$PYTHONPATH

# Preflight import check to fail fast
RUN python -c "import crewai; import pytest; print('preflight ok')"

# Default command to run tests
CMD ["pytest", "-v", "--tb=short"]