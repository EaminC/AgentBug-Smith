FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire repository
COPY . .

# Install dependencies conditionally
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
RUN if [ -f requirements-dev.txt ]; then pip install -r requirements-dev.txt; fi

# Install the package in editable mode unconditionally
RUN pip install -e .

# Handle potential monorepo structure - check for src or package directories
RUN if [ -d src ]; then \
        export PYTHONPATH=/app/src:$PYTHONPATH; \
    else \
        export PYTHONPATH=/app:$PYTHONPATH; \
    fi

# Set environment variables for API keys (inherited from build args or host)
ENV PYTHONPATH=/app:$PYTHONPATH
ENV FORGE_API_KEY="${FORGE_API_KEY}"
ENV FORGE_BASE_URL="${FORGE_BASE_URL}"
ENV MODEL="${MODEL}"
ENV AI_TEMPERATURE="${AI_TEMPERATURE}"
ENV ANTHROPIC_BASE_URL="${ANTHROPIC_BASE_URL}"
ENV ANTHROPIC_AUTH_TOKEN="${ANTHROPIC_AUTH_TOKEN}"
ENV ANTHROPIC_MODEL="${ANTHROPIC_MODEL}"
ENV ANTHROPIC_SMALL_FAST_MODEL="${ANTHROPIC_SMALL_FAST_MODEL}"
ENV OPENAI_BASE_URL="${OPENAI_BASE_URL}"
ENV OPENAI_API_KEY="${OPENAI_API_KEY}"
ENV TAVILY_API_KEY="${TAVILY_API_KEY}"
ENV GITHUB_TOKEN="${GITHUB_TOKEN}"

# Verify critical imports work
RUN python -c "from agentscope.formatter import DashScopeChatFormatter; print('DashScopeChatFormatter imported successfully')"