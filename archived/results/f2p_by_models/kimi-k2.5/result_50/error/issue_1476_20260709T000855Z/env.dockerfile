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

WORKDIR /app

# Install system dependencies for compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libxml2-dev \
    libxslt1-dev \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install build tools
RUN python -m pip install --upgrade pip wheel setuptools

# Copy the entire repository
COPY . .

# Set PYTHONPATH for src layout (package is at /app/src/agentscope)
ENV PYTHONPATH=/app/src

# Install project dependencies and the project itself
# For src layout with pyproject.toml, install in editable mode
RUN if [ -f "pyproject.toml" ]; then \
        pip install --no-cache-dir -e .; \
    elif [ -f "setup.py" ]; then \
        pip install --no-cache-dir -e .; \
    fi

# Install test dependencies
RUN pip install --no-cache-dir \
    pytest \
    pytest-mock \
    pytest-asyncio \
    pytest-cov \
    pytest-xdist \
    pytest-timeout \
    pytest-forked \
    anyio \
    "setuptools<=81.0.0" \
    litellm \
    mem0ai

# Set Forge API environment variables for OpenAI SDK compatibility
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key

# Set Forge API environment variables for Anthropic SDK compatibility
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co
ENV ANTHROPIC_AUTH_TOKEN=forge-key

# Verify the installation works
RUN python -c "import sys; sys.path.insert(0, '/app/src'); import agentscope; print('agentscope imported successfully')"

# Verify test dependencies
RUN python -c "import pytest; print('pytest imported successfully')"

CMD ["/bin/bash"]
