# CrewAI Dockerfile with Forge API Configuration
FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
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
# --- end inject ---

# Set working directory
WORKDIR /app

# Install system dependencies for compilation and general use
# Using --fix-missing and retry to handle transient network issues
RUN apt-get update || (sleep 5 && apt-get update) && \
    apt-get install -y --fix-missing --no-install-recommends \
    gcc \
    g++ \
    libxml2-dev \
    libxslt1-dev \
    python3-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install wheel
RUN python -m pip install --upgrade pip wheel

# Install uv for faster package management
RUN pip install uv

# Copy the entire repository
COPY . .

# Install project dependencies using uv if uv.lock exists, otherwise use pip
RUN if [ -f "uv.lock" ]; then \
        uv pip install --system -e .; \
    else \
        pip install -e .; \
    fi

# Install core framework SDK (CrewAI)
RUN pip install "crewai>=0.86.0"

# Install test dependencies explicitly
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov pytest-timeout \
    pytest-vcr pytest-subprocess \
    "setuptools<=81.0.0" \
    litellm \
    mem0ai \
    anyio \
    vcrpy

# Install optional dependencies for full functionality
RUN pip install tiktoken crewai-tools openai instructor

# Handle src/ layout by setting PYTHONPATH (avoid undefined variable)
ENV PYTHONPATH=/app/src

# Forge API Environment Variables for OpenAI SDK compatibility
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key

# Forge API Environment Variables for Anthropic SDK compatibility
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co
ENV ANTHROPIC_AUTH_TOKEN=forge-key

# Additional environment variables from project
ENV FORGE_API_KEY=forge-key
ENV FORGE_BASE_URL=https://api.forge.tensorblock.co/v1
ENV MODEL=tuzi-kimi-k2.5/kimi-k2.5
ENV ANTHROPIC_MODEL=tuzi-kimi-k2.5/kimi-k2.5
ENV ANTHROPIC_SMALL_FAST_MODEL=tuzi-kimi-k2.5/kimi-k2.5

# AI Configuration
ENV AI_TEMPERATURE=0.7
ENV AI_MAX_TOKENS=1000
ENV AI_TOP_P=1
ENV AI_FREQUENCY_PENALTY=0
ENV AI_PRESENCE_PENALTY=0

# Preflight check - verify key imports work
RUN python -c "import crewai; import pytest; print('preflight ok')"

# Final command
CMD ["/bin/bash"]
