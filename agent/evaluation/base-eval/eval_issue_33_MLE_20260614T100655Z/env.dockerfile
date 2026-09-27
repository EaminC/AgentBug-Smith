FROM python:3.12-slim AS test_builder

# --- Universal Build & Dynamic Versioning Overrides ---
ENV SETUPTOOLS_SCM_PRETEND_VERSION="0.0.1.dev0"
ENV POETRY_DYNAMIC_VERSIONING_BYPASS="0.0.1.dev0"
ENV HATCH_VCS_RECORD_FILE="/tmp/_version.py"
RUN git config --global --add safe.directory '*' || true
# -----------------------------------------------------


# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tuzi-deepseek-v3.2/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tuzi/deepseek-v3.2"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi/deepseek-v3.2"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

WORKDIR /app

# Install system dependencies required for building packages
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    git \
    libssl-dev \
    libffi-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy entire repository
COPY . .

# Upgrade pip, setuptools, wheel early
RUN python -m pip install --upgrade pip setuptools wheel

# Install base build dependencies
RUN pip install --upgrade "setuptools<=81.0.0" "wheel" "pip"

# Install constraints to fix compatibility issues upfront
# numpy<2.0 avoids chromadb compatibility issues with np.float_
# huggingface_hub==0.17.3 provides ModelFilter that agent.integration requires
RUN pip install --upgrade "numpy<2.0" "huggingface_hub==0.17.3"

# Install dependencies from requirements.txt first
RUN pip install -r requirements.txt

# Install the project in editable mode
RUN pip install -e .

# Install test dependencies
RUN pip install \
    pytest \
    pytest-mock \
    pytest-asyncio \
    pytest-cov \
    pytest-xdist \
    pytest-timeout \
    litellm \
    mem0ai \
    embedchain \
    anyio

# Preflight check to ensure key packages are importable
RUN python -c 'import sys; import os; import json; import openai; import pytest; print("preflight ok: sys, os, json, openai, pytest all importable")'

CMD ["/bin/bash"]