FROM python:3.12-slim AS test_builder

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

# Set Forge environment variables
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co
ENV ANTHROPIC_AUTH_TOKEN=forge-key

# Copy the entire repository
COPY . .

# Configure PYTHONPATH for multi-package layouts
ENV PYTHONPATH=/app/python:/app/python/src:/app/src:/app/lib:/app/libs:$PYTHONPATH

# Upgrade packaging tools and install dependencies
RUN set -ex && \
    cd python && \
    python -m pip install --upgrade pip setuptools wheel && \
    # Try uv if uv.lock exists, else fallback to pip
    if [ -f "uv.lock" ]; then \
        uv sync --locked --all-extras --dev; \
    elif [ -f "requirements.txt" ]; then \
        pip install -r requirements.txt; \
    fi && \
    # Install project in editable mode unconditionally
    if [ -f "setup.py" ] || [ -f "pyproject.toml" ]; then \
        pip install -e .; \
    fi && \
    # Install sub-packages if they exist
    if [ -d "libs" ]; then \
        find libs -name "setup.py" -o -name "pyproject.toml" | while read f; do \
            dir=$(dirname "$f"); \
            echo "Installing $dir in editable mode"; \
            pip install -e "$dir"; \
        done; \
    fi && \
    # Install mandatory test dependencies
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Preflight import check - actually test imports
RUN cd python && python -c "\
try: \
    import pytest; \
    import litellm; \
    print('preflight ok - core imports work'); \
except ImportError as e: \
    print(f'preflight failed: {e}'); \
    exit(1); \
"

# Default command to run tests
CMD ["pytest", "-v", "--tb=short", "python/tests/"]