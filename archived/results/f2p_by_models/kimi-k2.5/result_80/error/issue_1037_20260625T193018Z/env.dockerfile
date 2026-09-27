FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy source code
COPY . .

# Install dependencies safely if they exist
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi
RUN if [ -f requirements-dev.txt ]; then pip install --no-cache-dir -r requirements-dev.txt; fi

# Install the package in editable mode (CRITICAL for monorepo/multi-package)
RUN pip install -e .

# Handle potential sub-packages if this is a monorepo
# Check for common monorepo patterns and install accordingly
RUN if [ -d src ]; then \
        pip install -e src/ 2>/dev/null || true; \
    fi

# Set PYTHONPATH to include all potential source directories
ENV PYTHONPATH=/app:/app/src:/app/libs:$PYTHONPATH

# Install pytest for test execution
RUN pip install pytest pytest-asyncio

# Environment variables for API access (dynamic retrieval in tests)
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

# Default command to run tests
CMD ["pytest", "-v"]