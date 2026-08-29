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

# Copy entire repository (mandatory for external test scripts)
COPY . .

# Install system dependencies if any are needed (based on CI evidence)
RUN apt-get update && apt-get install -y --no-install-recommends \
    make \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies - prioritize uv if available, otherwise use pip
RUN python -m pip install --upgrade pip wheel setuptools

# First install the project in editable mode (CRITICAL)
RUN pip install -e .

# Then install test dependencies based on what's available
RUN if [ -f pyproject.toml ]; then \
        # Check if uv is configured in pyproject.toml
        if grep -q "uv" pyproject.toml; then \
            pip install uv && \
            uv pip install -e . --group dev; \
        else \
            pip install pytest pytest-mock pytest-asyncio pytest-cov anyio pytest-xdist pytest-timeout; \
        fi; \
    else \
        # Fallback to installing common test dependencies
        pip install pytest pytest-mock pytest-asyncio pytest-cov anyio pytest-xdist pytest-timeout; \
    fi

# Install additional dependencies if requirements files exist
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
RUN if [ -f requirements-dev.txt ]; then pip install -r requirements-dev.txt; fi
RUN if [ -f requirements-test.txt ]; then pip install -r requirements-test.txt; fi

# Handle monorepo layouts - install sub-packages if they exist
RUN if [ -d libs ]; then \
        find libs -name "pyproject.toml" -o -name "setup.py" | while read f; do \
            dir=$(dirname "$f"); \
            pip install -e "$dir"; \
        done; \
    fi

# Set PYTHONPATH for monorepo support
ENV PYTHONPATH=/app

# Preflight import check
RUN python -c "import pytest; print('pytest version:', pytest.__version__)"

# Default command to run tests
CMD ["pytest", "-v", "--tb=short"]