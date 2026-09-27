FROM python:3.12-slim

# --- Universal Build & Dynamic Versioning Overrides ---
ENV SETUPTOOLS_SCM_PRETEND_VERSION="0.0.1.dev0"
ENV POETRY_DYNAMIC_VERSIONING_BYPASS="0.0.1.dev0"
ENV HATCH_VCS_RECORD_FILE="/tmp/_version.py"
RUN git config --global --add safe.directory '*' || true
ENV SETUPTOOLS_SCM_PRETEND_VERSION_FOR_STRANDS_MONOREPO_TOOLS="0.0.1.dev0"
# -----------------------------------------------------


# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tuzi-deepseek-v3.2/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tuzi-deepseek-v3.2/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi-deepseek-v3.2/gpt-4.1-mini"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

# Set working directory
WORKDIR /app

# Copy entire repository
COPY . .

# Install system dependencies including Node.js and npm
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       git \
       gcc \
       python3-dev \
       libffi-dev \
       libssl-dev \
       nodejs \
       npm \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip, setuptools, wheel
RUN python -m pip install --upgrade pip setuptools wheel

# Install Python dependencies including missing 'moto' package for tests
RUN set -eux; \
    if [ -f requirements.txt ]; then pip install -r requirements.txt; fi; \
    pip install -e strands-py; \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio moto "setuptools<=81.0.0" litellm anthropic mistralai ollama google-genai

# Preflight check that essential packages are installed
RUN python -c 'import pkg_resources, pytest, moto; print("preflight ok")'

# Set PYTHONPATH to include /app and sub-package paths for local imports
ENV AWS_ACCESS_KEY_ID="testing"
ENV AWS_SECRET_ACCESS_KEY="testing"
ENV AWS_SECURITY_TOKEN="testing"
ENV AWS_SESSION_TOKEN="testing"
ENV AWS_DEFAULT_REGION="us-east-1"
ENV PYTHONPATH=/app

CMD ["/bin/bash"]