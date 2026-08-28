# branch: python/requirements.txt
FROM python:3.12-slim

# --- Universal Build & Dynamic Versioning Overrides ---
ENV SETUPTOOLS_SCM_PRETEND_VERSION="0.0.1.dev0"
ENV POETRY_DYNAMIC_VERSIONING_BYPASS="0.0.1.dev0"
ENV HATCH_VCS_RECORD_FILE="/tmp/_version.py"
RUN git config --global --add safe.directory '*' || true
# -----------------------------------------------------


# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tuzi-gpt-4.1-mini/gpt-4.1-mini"
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
ENV AI_MAX_TOKENS=1000
ENV AI_TOP_P=1
ENV AI_FREQUENCY_PENALTY=0
ENV AI_PRESENCE_PENALTY=0
ENV AI_STOP_SEQUENCES="[]"

WORKDIR /app

# Install system dependencies for Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    libxml2-dev \
    libxslt1-dev \
    python3-dev \
    gcc \
    portaudio19-dev \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment to avoid PEP 668 issues
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"
ENV VIRTUAL_ENV="/venv"

# Upgrade packaging tools early
RUN pip install --upgrade pip setuptools wheel

# Copy entire repository (including externally-injected tests)
COPY . .

# Install project dependencies from requirements.txt and the project itself
# First install requirements.txt, then install project in development mode
RUN if [ -f "requirements.txt" ]; then \
    pip install -r requirements.txt; \
    fi

# Install the project itself in development mode
RUN pip install -e .

# Install testing dependencies
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov pytest-xdist pytest-timeout anyio

# Install any additional dependencies that might be missing
RUN pip install backoff beautifulsoup4 configargparse diff-match-patch diskcache \
    flake8 gitpython grep-ast importlib-metadata importlib-resources json5 jsonschema \
    networkx numpy packaging pathspec pexpect pillow prompt-toolkit psutil \
    pydub pypandoc pyperclip python-dotenv pyyaml rich scipy sounddevice soundfile \
    tokenizers tree-sitter tree-sitter-languages

# Set PYTHONPATH to include /app for module imports
ENV PYTHONPATH=/app

# Verify critical imports work
RUN python -c "import aider; print('aider imported successfully')"
RUN python -c "from aider.coders.base_coder import Coder; print('Coder imported successfully')"
RUN python -c "from aider.llm import litellm; print('litellm imported successfully')"
RUN python -c "from aider.models import Model; print('Model imported successfully')"
RUN python -c "import pytest; print('pytest imported successfully')"

# Test that main application can run
RUN python -c "from aider.main import main; print('main function imported successfully')"

# Test standalone script execution capability
RUN python -c "import sys, os, json, requests; print('Standard libraries imported successfully')"

# Preflight check - use importlib.metadata instead of pkg_resources for Python 3.12
RUN python -c 'import importlib.metadata, pytest, aider; print("preflight ok")'

# Final CMD as required by test harness
CMD ["/bin/bash"]