FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="openrouter3/openai/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="openrouter3/openai/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="openrouter3/openai/gpt-4.1-mini"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

# Set working directory in the container
WORKDIR /app

# Set environment variables for Forge API compatibility
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co
ENV ANTHROPIC_AUTH_TOKEN=forge-key

# Also set injected environment variables from .env for completeness
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="openrouter3/openai/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV AI_MAX_TOKENS="1000"
ENV AI_TOP_P="1"
ENV AI_FREQUENCY_PENALTY="0"
ENV AI_PRESENCE_PENALTY="0"
ENV AI_STOP_SEQUENCES=""
ENV ANTHROPIC_MODEL="openrouter3/openai/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="openrouter3/openai/gpt-4.1-mini"
ENV TAVILY_API_KEY="tvly-key"
ENV GITHUB_TOKEN="ghp_key"

# Install system dependencies for building some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libxml2-dev libxslt1-dev python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy entire repo to container
COPY . .

# Upgrade pip and setuptools
RUN python -m pip install --upgrade pip setuptools wheel

# Install dependencies and the package itself, plus required test tools
RUN if [ -f "requirements.txt" ]; then \
        pip install --no-cache-dir -r requirements.txt; \
    fi && \
    pip install --no-cache-dir -e . && \
    pip install --no-cache-dir \
        pytest pytest-mock pytest-asyncio pytest-cov anyio pytest-timeout \
        "setuptools<=81.0.0" litellm

# Set PYTHONPATH for src/ layout
ENV PYTHONPATH=/app:/app/src

# Use bash as default command for tests and interaction
CMD ["/bin/bash"]

# branch: python/requirements.txt
