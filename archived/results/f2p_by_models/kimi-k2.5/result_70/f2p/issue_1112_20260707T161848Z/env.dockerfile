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

# Install system dependencies for potential compilation (lxml, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libxml2-dev \
    libxslt1-dev \
    python3-dev \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install core build tools
RUN python -m pip install --upgrade pip wheel setuptools

# Copy entire repository first (needed for installation)
COPY . .

# Install dependencies via pip using quotes to handle version specifiers with special characters
RUN pip install \
    "openai>=1.0" \
    "termcolor==2.3.0" \
    "typer>=0.3.2" \
    "rudder-sdk-python>=2.0.2" \
    "dataclasses-json==0.5.7" \
    "tiktoken>=0.0.4" \
    "tabulate==0.9.0" \
    "python-dotenv>=0.21.0" \
    "langchain>=0.1,<0.2" \
    "langchain_openai" \
    "toml>=0.10.2" \
    "tomlkit>=0.12.4" \
    "pyperclip>=1.8.2" \
    "langchain-anthropic>=0.1.1" \
    "regex>=2023.12.25" \
    "pillow>=10.2.0" \
    "datasets>=2.17.1"

# Install the project itself in editable mode
RUN pip install -e .

# Install test dependencies via pip
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio pytest-xdist pytest-timeout litellm mem0ai

# Pre-flight check - verify gpt_engineer and pytest are importable
RUN python -c 'import gpt_engineer; print("gpt_engineer imported successfully")' && \
    python -c 'import pytest; print("pytest imported successfully")' && \
    echo "preflight ok"

CMD ["/bin/bash"]
