FROM python:3.12-slim

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

# Copy entire repository context
COPY . .

# Set PYTHONPATH for multi-package layouts
ENV PYTHONPATH=/app:/app/src:/app/lib:/app/libs:/app/packages:$PYTHONPATH

# Detect package manager and install dependencies with robust error handling
RUN set -eux && \
    # Upgrade pip, setuptools, wheel
    python -m pip install --upgrade pip wheel setuptools && \
    # Install uv if uv.lock exists (based on CI workflows)
    if [ -f "uv.lock" ]; then \
        pip install uv && \
        uv sync --frozen --group dev; \
    elif [ -f "pyproject.toml" ] && [ -f "poetry.lock" ]; then \
        pip install poetry && \
        poetry config virtualenvs.create false && \
        poetry install --no-interaction --no-ansi; \
    elif [ -f "requirements.txt" ]; then \
        pip install -r requirements.txt; \
    fi && \
    # Install the local package in development mode (unconditionally)
    if [ -f "setup.py" ] || [ -f "pyproject.toml" ]; then \
        pip install -e .; \
    fi && \
    # Install sub-packages if they exist
    if [ -d "libs" ]; then \
        find libs -name "pyproject.toml" -o -name "setup.py" | while read pkg; do \
            dir=$(dirname "$pkg"); \
            pip install -e "$dir"; \
        done; \
    fi && \
    if [ -d "packages" ]; then \
        find packages -name "pyproject.toml" -o -name "setup.py" | while read pkg; do \
            dir=$(dirname "$pkg"); \
            pip install -e "$dir"; \
        done; \
    fi && \
    # Mandatory test dependencies
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio pytest-xdist pytest-timeout mem0ai

# Verify critical imports work
RUN python -c "import pytest; import os; print('Environment check passed')"

CMD ["/bin/bash"]