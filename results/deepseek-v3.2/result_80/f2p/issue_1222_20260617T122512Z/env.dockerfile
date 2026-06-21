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

# Set Forge API environment variables
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV AI_TEMPERATURE="0.7"
ENV AI_MAX_TOKENS=1000
ENV AI_TOP_P=1
ENV AI_FREQUENCY_PENALTY=0
ENV AI_PRESENCE_PENALTY=0

# For OpenAI SDK compatibility
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"

# For Anthropic SDK compatibility (Note: Anthropic uses /v1 path for Forge)
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"

# Additional API keys
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"

WORKDIR /app

# Copy entire repository (required for injected tests)
COPY . .

# Install system dependencies needed for Python packages
# Based on requirements: sounddevice, soundfile, tree-sitter, pypandoc need system libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    portaudio19-dev \
    libsndfile1 \
    libasound2-dev \
    libportaudio2 \
    libportaudiocpp0 \
    pandoc \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install setuptools with version constraint
RUN python -m pip install --upgrade pip wheel && \
    pip install "setuptools<=81.0.0"

# Install project dependencies from requirements.txt
# Use --break-system-packages to handle PEP 668 system package protection
RUN if [ -f requirements.txt ]; then pip install --break-system-packages -r requirements.txt; fi

# Install the project in editable mode (handles both setup.py and pyproject.toml)
RUN pip install --break-system-packages -e .

# Install test dependencies (including litellm and mem0ai as required by instructions)
RUN pip install --break-system-packages \
    pytest pytest-mock pytest-asyncio pytest-cov pytest-xdist pytest-timeout \
    litellm mem0ai anyio

# Preflight import check - verify critical packages can be imported
RUN python -c "import setuptools; import pytest; import aider; import litellm; import anyio; import git; import prompt_toolkit; print('preflight ok: setuptools, pytest, aider, litellm, anyio, git, prompt_toolkit')"

# Set PYTHONPATH to ensure imports work correctly
ENV PYTHONPATH=/app

# Final command required by test harness
CMD ["/bin/bash"]