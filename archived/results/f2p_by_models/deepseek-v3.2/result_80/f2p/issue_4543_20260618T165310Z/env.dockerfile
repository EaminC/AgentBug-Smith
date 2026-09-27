# branch: python/requirements.txt
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

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    libportaudio2 \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy entire repository (including injected tests)
COPY . .

# Upgrade pip and install build tools
RUN python -m pip install --upgrade pip setuptools wheel

# Install project dependencies and the project itself
# Check for requirements.txt first
RUN if [ -f "requirements.txt" ]; then \
    pip install -r requirements.txt && \
    pip install -e .; \
    else \
    pip install -e .; \
    fi

# Install test dependencies (required for running tests)
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov pytest-xdist pytest-timeout

# Install additional AI framework packages
RUN pip install litellm "setuptools<=81.0.0"

# Set environment variables for Forge API
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1
ENV ANTHROPIC_AUTH_TOKEN=forge-key
ENV AIDER_ANALYTICS=false

# Set Python path
ENV PYTHONPATH=/app

# Verify installation
RUN python -c "import aider; import pytest; print('Installation verified')"

# Final command - required for test harness
CMD ["/bin/bash"]