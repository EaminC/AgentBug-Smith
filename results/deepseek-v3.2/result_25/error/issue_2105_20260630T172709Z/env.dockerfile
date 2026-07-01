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

# Install system dependencies for building python packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        git \
        && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy entire repository (required for external test scripts)
COPY . .

# Upgrade pip and setuptools
RUN python -m pip install --upgrade pip wheel

# Detect package manager and install dependencies
# Based on pyproject.toml and uv (tool.uv) usage in CI
# The project uses uv for dev dependencies, but install via pip for production
# We'll install using pip with uv as fallback if uv.lock exists
RUN if [ -f uv.lock ]; then \
        pip install uv && \
        uv venv && \
        uv sync --dev --all-extras; \
    elif [ -f requirements.txt ]; then \
        pip install -r requirements.txt; \
    fi && \
    # Install the package in editable mode (no src/ layout detected)
    pip install -e . && \
    # Mandatory test dependencies (must be installed)
    pip install pytest pytest-mock pytest-asyncio pytest-cov pytest-xdist pytest-timeout "setuptools<=81.0.0" litellm anyio mem0ai

# Preflight import check to fail fast if core modules are missing
RUN python -c "import crewai, pydantic, litellm; print('preflight ok')"

# Default command (as per test harness requirement)
CMD ["/bin/bash"]