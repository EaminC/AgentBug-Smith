FROM python:3.12-slim

# branch: python/pyproject.toml with Forge API configuration for Dapr Agents project

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

# Set environment variables for Forge API (OpenAI SDK compatibility)
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co
ENV ANTHROPIC_AUTH_TOKEN=forge-key

# Set SETUPTOOLS_SCM_PRETEND_VERSION to avoid git dependency issues during build
ENV SETUPTOOLS_SCM_PRETEND_VERSION=1.0.0

WORKDIR /app

# Upgrade pip and setuptools
RUN python -m pip install --upgrade pip setuptools wheel

# Install system dependencies for building Python packages
# Includes git for setuptools_scm and other build essentials
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire repository (required for injected tests)
COPY . .

# First install compatible protobuf version that works with all dependencies
# Based on error analysis: gencode 6.31.1 needs runtime >= 6.31.1
# But other packages require protobuf < 6.0
# Let's try a middle ground
RUN pip install "protobuf>=5.29.6,<6.0.0"

# Install the project with test dependencies but skip dependency resolution for protobuf
# We'll install dependencies manually to avoid conflicts
RUN pip install --no-deps -e .

# Install core dependencies manually to control versions
RUN pip install \
    "pydantic>=2.11.3,<3.0.0" \
    "jinja2>=3.1.0,<4.0.0" \
    "pyyaml>=6.0,<7.0.0" \
    "requests>=2.31.0,<3.0.0" \
    "openapi-pydantic>=0.3.0,<0.4.0" \
    "openapi-schema-pydantic>=1.2.4,<2.0.0" \
    "rich>=13.9.4,<14.0.0" \
    "openai>=1.75.0,<2.0.0" \
    "azure-identity>=1.21.0,<2.0.0" \
    "huggingface_hub>=0.30.2,<1.0.0" \
    "colorama>=0.4.6,<1.0.0" \
    "regex>=2023.0.0,<2025.0.0" \
    "fastapi>=0.110.0,<1.0.0" \
    "uvicorn>=0.27.0,<1.0.0" \
    "aiohttp>=3.9.0,<4.0.0" \
    "cloudevents>=1.11.0,<2.0.0" \
    "numpy>=2.2.2,<3.0.0" \
    "mcp>=1.7.1,<2.0.0" \
    "opentelemetry-api>=1.12.0,<1.35.0" \
    "opentelemetry-distro>=0.53b1,<0.56b0" \
    "opentelemetry-exporter-otlp>=1.32.1,<1.35.0" \
    "opentelemetry-instrumentation-requests>=0.53b1,<0.56b0" \
    "pip-tools>=7.4.1,<8.0.0" \
    "sentence-transformers>=4.1.0,<5.0.0" \
    "chromadb>=1.0.13,<2.0.0" \
    "posthog<6.0.0"

# Install test dependencies
RUN pip install \
    "pytest>=7.0.0,<8.0.0" \
    "pytest-asyncio>=0.23.0,<1.0.0" \
    "pytest-cov>=4.1.0,<5.0.0" \
    "pytest-mock>=3.12.0,<4.0.0" \
    "pytest-xdist>=3.3.1,<4.0.0" \
    "pytest-timeout>=2.1.0,<3.0.0" \
    "httpx>=0.27.0,<1.0.0" \
    "setuptools<=81.0.0" \
    "litellm<=1.80.0" \
    "mem0ai>=0.1.0,<1.0.0" \
    "anyio>=4.0.0,<5.0.0"

# Try to install Dapr dependencies with constraints
RUN pip install "dapr>=1.13.0" "dapr-ext-grpc>=1.13.0" "dapr-ext-fastapi>=1.15.0" "dapr-ext-workflow>=1.15.0" || echo "Dapr installation may have issues"

# Try to install durabletask-dapr - if it fails due to protobuf, we'll continue anyway
RUN pip install "durabletask-dapr>=0.2.0a7" || echo "durabletask-dapr installation failed, tests will use mocked modules"

# Set PYTHONPATH for module resolution
ENV PYTHONPATH=/app

# Basic import checks
RUN python -c 'import sys; import os; import json; print("Basic imports successful")'
RUN python -c 'import pytest; print("pytest import successful")'
RUN python -c 'import jinja2; print("jinja2 import successful")'

# Verify the environment is configured for Forge API
RUN python -c 'import os; print("OPENAI_BASE_URL:", os.getenv("OPENAI_BASE_URL")); print("ANTHROPIC_BASE_URL:", os.getenv("ANTHROPIC_BASE_URL"))'

# Try test collection - even if imports fail, tests might work with mocks
RUN echo "Testing pytest collection..." && python -m pytest --collect-only tests/ 2>&1 | grep -E "collected|ERROR|FAILED|warning" | head -30

# Preflight check as per instructions
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Required for test harness
CMD ["/bin/bash"]