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

# Environment variables for Forge API compatibility
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co \
    ANTHROPIC_AUTH_TOKEN=forge-key

# Set working directory
WORKDIR /app

# Install system dependencies required for Python build and xml libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libxml2-dev \
    libxslt1-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy entire repository into working directory
COPY . .

# Upgrade pip, setuptools, and wheel
RUN python -m pip install --upgrade pip setuptools wheel

# Install project in editable mode unconditionally
RUN pip install -e .

# Install testing dependencies (excluding pytest-block-network which is not found)
RUN pip install --no-cache-dir pytest pytest-mock pytest-asyncio pytest-cov anyio pytest-timeout "setuptools<=81.0.0" litellm

# Set PYTHONPATH for the src/ layout
ENV PYTHONPATH=/app:/app/src

# Default command line
CMD ["/bin/bash"]