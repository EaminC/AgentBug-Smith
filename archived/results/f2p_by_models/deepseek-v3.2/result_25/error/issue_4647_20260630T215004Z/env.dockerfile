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

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy entire repository
COPY . .

# First, install the project in editable mode
RUN pip install --upgrade pip wheel

# Check for pyproject.toml or setup.py to determine installation method
RUN if [ -f pyproject.toml ]; then \
        pip install -e .; \
    elif [ -f setup.py ]; then \
        pip install -e .; \
    else \
        echo "No pyproject.toml or setup.py found"; \
    fi

# Install test dependencies
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio litellm pytest-xdist pytest-timeout

# Install additional dependencies if requirements files exist
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
RUN if [ -f requirements-dev.txt ]; then pip install -r requirements-dev.txt; fi
RUN if [ -f test-requirements.txt ]; then pip install -r test-requirements.txt; fi

# Set PYTHONPATH to include the current directory
ENV PYTHONPATH=/app:$PYTHONPATH

# Set environment variable for telemetry opt-out
ENV OTEL_SDK_DISABLED=true

# Run tests by default
CMD ["pytest", "-v", "--tb=short"]