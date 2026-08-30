FROM python:3.12-slim

# --- Universal Build & Dynamic Versioning Overrides ---
ENV SETUPTOOLS_SCM_PRETEND_VERSION="0.0.1.dev0"
ENV POETRY_DYNAMIC_VERSIONING_BYPASS="0.0.1.dev0"
ENV HATCH_VCS_RECORD_FILE="/tmp/_version.py"
RUN git config --global --add safe.directory '*' || true
ENV SETUPTOOLS_SCM_PRETEND_VERSION_FOR_DAPR_AGENTS="0.0.1.dev0"
# -----------------------------------------------------


# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="openai/tuzi-gpt-4.1-mini/gpt-4.1-mini"
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

# Upgrade packaging tools early
RUN python -m pip install --upgrade pip setuptools wheel

# Install system dependencies including git for setuptools-scm
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set Forge environment variables (required for test harness)
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN=forge-key
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL=https://api.forge.tensorblock.co/v1

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

# Install additional packages that might be needed for quickstarts
# Commenting out problematic packages to get build working
# RUN pip install elevenlabs==1.6.0 \
#     nvidia-pyindex \
#     chromadb>=0.4.24 \
#     psycopg2-binary>=2.9.9 \
#     sentence-transformers>=2.2.2 \
#     pypdf>=4.2.0 \
#     pymupdf>=1.24.4 \
#     tiktoken

# Install NVIDIA package after nvidia-pyindex
# RUN pip install nvidia-nim-client

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