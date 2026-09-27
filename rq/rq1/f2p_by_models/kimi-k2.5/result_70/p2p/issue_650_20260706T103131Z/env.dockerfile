# GPT-Engineer Dockerfile with Forge API Configuration
FROM python:3.11-slim

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

# Install system dependencies including tkinter libraries required by gpt_engineer
# Use apt to install tkinter without hardcoding specific library versions
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libxml2-dev \
    libxslt1-dev \
    python3-dev \
    python3-tk \
    tk-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set library path for tkinter shared libraries
ENV LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH

# Upgrade pip and install wheel
RUN pip install --upgrade pip wheel "setuptools<=81.0.0"

# Copy the entire repository
COPY . .

# Install dependencies with exact compatible versions FIRST
# The codebase requires specific older versions due to breaking changes in newer packages
RUN pip install \
    openai==0.27.8 \
    langchain==0.0.300 \
    "tiktoken>=0.0.4" \
    python-dotenv==0.21.1 \
    "click>=8.0.0" \
    "typer>=0.3.2" \
    termcolor==2.3.0 \
    dataclasses-json==0.5.7 \
    tabulate==0.9.0 \
    rudder-sdk-python==2.0.2 \
    agent-protocol==1.0.1 \
    pydantic==1.10.26 \
    black==23.3.0 \
    mypy==1.3.0 \
    pre-commit==3.3.3 \
    ruff==0.0.272 \
    backoff==2.2.1 \
    pytest==7.3.1

# Install the project without dependencies (already installed above)
RUN pip install --no-deps -e .

# Install additional test dependencies
RUN pip install pytest-mock pytest-xdist pytest-timeout

# Set environment variables for Forge API (OpenAI-compatible)
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key

# Set environment variables for Anthropic SDK compatibility
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1
ENV ANTHROPIC_AUTH_TOKEN=forge-key

# Additional Forge configuration
ENV FORGE_API_KEY=forge-key
ENV FORGE_BASE_URL=https://api.forge.tensorblock.co/v1

# Preflight check - ensure Python and pytest are properly installed
RUN python -c "import gpt_engineer; print('gpt_engineer imported successfully')" && \
    python -c "import pytest; print('pytest imported successfully')" && \
    echo "preflight ok"

# Default command to start bash shell
CMD ["/bin/bash"]
