# Dockerfile for CrewAI project with Forge API configuration
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

# Set environment variables for Forge API
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

# Install system dependencies, Python packages, and clean up in a single layer to minimize disk usage
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        python3-dev \
        libffi-dev \
        libxml2-dev \
        libxslt1-dev \
        git \
        && \
    pip install --no-cache-dir --upgrade pip wheel "setuptools<=81.0.0" hatchling && \
    apt-get purge -y --auto-remove && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/* /tmp/* /var/tmp/* /root/.cache/*

# Copy the entire repository
COPY . .

# Install the crewai package and all test dependencies in a single RUN to reduce layers
RUN pip install --no-cache-dir -e . && \
    pip install --no-cache-dir \
        pytest>=8.0.0 \
        pytest-vcr>=1.0.2 \
        pytest-asyncio>=0.23.7 \
        pytest-subprocess>=1.5.2 \
        pytest-mock \
        pytest-xdist \
        pytest-timeout \
        pytest-cov \
        lxml \
        regex>=2024.9.11 \
        mem0ai>=0.1.29 \
        httpx \
        anyio \
        pillow \
        litellm \
        crewai-tools>=0.36.0 \
        tiktoken \
    && \
    rm -rf /root/.cache/* /tmp/* /var/tmp/*

# Set PYTHONPATH for src/ layout
ENV PYTHONPATH=/app/src

# Verify installation
RUN python -c "import sys; print(f'Python {sys.version}')" && \
    python -c "import pytest; print(f'pytest {pytest.__version__}')" && \
    python -c "from crewai import Agent, Crew, Task, LLM; print('CrewAI imports OK')"

CMD ["/bin/bash"]
