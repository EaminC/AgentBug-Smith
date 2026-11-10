FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="openrouter2/openai/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="openrouter2/openai/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="openrouter2/openai/gpt-4.1-mini"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

# Set environment variables for Forge API compatibility
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co
ENV ANTHROPIC_AUTH_TOKEN=forge-key

# Set working directory
WORKDIR /app

# Install system dependencies needed for Python packages that require compilation or libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    python3-dev \
    libffi-dev \
    libssl-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy entire repo into container
COPY . .

# Upgrade pip, setuptools, wheel
RUN python -m pip install --upgrade pip setuptools wheel

# Install Python dependencies including requirements.txt and test tools
RUN if [ -f requirements.txt ]; then \
      pip install -r requirements.txt; \
    fi && \
    pip install -e . && \
    pip install --no-cache-dir pytest pytest-mock pytest-asyncio pytest-cov anyio pytest-timeout "setuptools<=81.0.0" litellm

# Set PYTHONPATH for module import (assuming no src/ directory detected, just /app)
ENV PYTHONPATH=/app

# Default command for test harness
CMD ["/bin/bash"]

# branch: python/requirements.txt
