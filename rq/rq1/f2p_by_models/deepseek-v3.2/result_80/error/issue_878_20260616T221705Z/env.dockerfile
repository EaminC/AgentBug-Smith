# branch: python/poetry with Python 3.12-slim
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

WORKDIR /app

# Update package lists and install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    gcc \
    g++ \
    libxml2-dev \
    libxslt1-dev \
    libssl-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry with retry for network issues
RUN pip install --upgrade pip && \
    pip install poetry==1.5.1

# Copy entire repository
COPY . .

# Navigate to platform directory for installation
WORKDIR /app/platform

# Configure Poetry to not create virtual environment (install in system)
RUN poetry config virtualenvs.create false

# First install typing_extensions to a compatible version to avoid conflicts with pytest-asyncio
RUN pip install --break-system-packages typing_extensions>=4.12.0

# Install project dependencies with poetry (with retry)
RUN poetry install --no-interaction --no-ansi || \
    (echo "First poetry install failed, retrying..." && sleep 5 && poetry install --no-interaction --no-ansi)

# Install required test dependencies as per instructions
# Use specific versions that are compatible with the project's old dependencies
RUN pip install --break-system-packages \
    pytest-xdist \
    pytest-timeout \
    pytest-mock \
    pytest-asyncio \
    setuptools==81.0.0 \
    litellm==0.1.0  # Try a much older version that might work with openai 0.27.x

# Install the project in development mode
RUN pip install --break-system-packages -e .

# Set Python path for src/ layout
ENV PYTHONPATH=/app:/app/platform

# Set environment variables for Forge API compatibility (redundant but ensures they're set)
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1
ENV ANTHROPIC_AUTH_TOKEN=forge-key
ENV MODEL=tuzi-deepseek-v3.2/deepseek-v3.2
ENV AI_TEMPERATURE=0.7
ENV AI_MAX_TOKENS=1000
ENV AI_TOP_P=1
ENV AI_FREQUENCY_PENALTY=0
ENV AI_PRESENCE_PENALTY=0
ENV ANTHROPIC_MODEL=tuzi-deepseek-v3.2/deepseek-v3.2
ENV ANTHROPIC_SMALL_FAST_MODEL=tuzi-deepseek-v3.2/deepseek-v3.2
ENV TAVILY_API_KEY=tvly-dev-key
ENV GITHUB_TOKEN=ghp_key
ENV REWORKD_PLATFORM_ENVIRONMENT=pytest
ENV REWORKD_PLATFORM_DB_BASE=reworkd_platform_test
ENV REWORKD_PLATFORM_SENTRY_DSN=

# Verify installation with import tests (fixed typing_extensions check)
RUN python -c 'import pytest; print(f"pytest {pytest.__version__}")'
RUN python -c 'import openai; print(f"openai {openai.__version__}")'
RUN python -c 'import pydantic; print(f"pydantic {pydantic.__version__}")'
RUN python -c 'import sys, os, json, requests; print("Standard libraries ok")'
RUN python -c 'import typing_extensions; print("typing_extensions imported"); from typing_extensions import TypeIs; print("TypeIs import successful")'
RUN python -c 'import aiohttp; print(f"aiohttp {aiohttp.__version__}")'
RUN python -c 'import reworkd_platform; print("reworkd_platform imported successfully")'

# Create tests directory if it doesn't exist
RUN mkdir -p /app/tests

# Set WORKDIR back to repository root for running scripts
WORKDIR /app

# Default command for test harness (required)
CMD ["/bin/bash"]