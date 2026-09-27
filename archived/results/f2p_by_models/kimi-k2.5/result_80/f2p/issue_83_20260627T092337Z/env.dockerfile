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

ENV SETUPTOOLS_SCM_PRETEND_VERSION="1.0.0"

WORKDIR /app

# Upgrade packaging tools early
RUN python -m pip install --upgrade pip setuptools wheel

# Install system dependencies including git for setuptools-scm
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy entire repository (including any externally injected test scripts)
COPY . .

# Install Dapr SDKs with consistent versions (critical for Dapr project)
# Install Dapr 1.15.0 exactly to match dapr-ext-fastapi==1.15.0 and dapr-ext-workflow==1.15.0
RUN pip install "dapr==1.15.0" "dapr-ext-grpc==1.15.0" "dapr-ext-fastapi==1.15.0" "dapr-ext-workflow==1.15.0"

# Install base dependencies from requirements.txt
RUN if [ -f "requirements.txt" ]; then \
    pip install -r requirements.txt; \
    fi

# Note: We're NOT doing 'pip install -e .' because setuptools-scm requires git
# and version detection. Instead, we rely on PYTHONPATH for imports.
# The package is at /app/dapr_agents and PYTHONPATH includes /app

# Install test frameworks and essential utilities
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio \
    "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai \
    python-dotenv

# Install packages for MCP support
RUN pip install mcp[cli]>=1.3.0

# Preflight import check to fail fast - also test importing dapr_agents
RUN python -c "\
import pkg_resources; \
import pytest; \
import dapr; \
import openai; \
import pydantic; \
import numpy; \
import dapr_agents; \
print('dapr_agents import ok')"

# Set PYTHONPATH to include current directory for imports
# This allows importing dapr_agents without 'pip install -e .'
ENV PYTHONPATH=/app:$PYTHONPATH

# Final command as required by test harness
CMD ["/bin/bash"]