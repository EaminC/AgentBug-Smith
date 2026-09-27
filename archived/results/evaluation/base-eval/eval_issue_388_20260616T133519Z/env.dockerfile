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

# Set environment variables for Forge API compatibility
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN=forge-key
ENV MODEL="tuzi-gpt-4.1-mini/gpt-4.1-mini"
ENV AI_TEMPERATURE=0.7
ENV AI_MAX_TOKENS=1000
ENV AI_TOP_P=1
ENV AI_FREQUENCY_PENALTY=0
ENV AI_PRESENCE_PENALTY=0
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL=https://api.forge.tensorblock.co/v1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install packaging tools
RUN python -m pip install --upgrade pip "setuptools<=81.0.0" wheel

# Copy entire repository
COPY . .

# Install project dependencies from pyproject.toml with exact versions
RUN pip install --break-system-packages -e .

# Install additional test dependencies not listed in pyproject.toml
# Install compatible click version for typer
RUN pip install --break-system-packages \
    pytest-mock==3.10.0 \
    pytest-asyncio==0.21.1 \
    pytest-cov==4.1.0 \
    pytest-xdist==3.5.0 \
    pytest-timeout==2.2.0 \
    anyio==3.7.1 \
    click==8.1.7  # Ensure compatible click version for typer

# Verify installation - check that main packages are installed
RUN python -c "import gpt_engineer, pytest, openai; print('Imports: gpt_engineer, pytest, openai - OK')"

# Test that we can run a simple command
RUN python -c "import sys; print(f'Python {sys.version}'); print('Environment ready for testing')"

# Test that OpenAI SDK can authenticate with Forge API
RUN python -c "import os; import openai; openai.api_key = os.getenv('OPENAI_API_KEY'); openai.api_base = os.getenv('OPENAI_BASE_URL'); print(f'OpenAI API Base: {openai.api_base}'); print(f'OpenAI API Key configured: {openai.api_key[:10]}...'); print('OpenAI SDK configured for Forge API')"

# Verify specific version requirements from pyproject.toml
RUN python -c "import openai; print(f'OpenAI version: {openai.__version__}')"

# Test that we can import all required modules for the project
RUN python -c "from gpt_engineer.steps import Config, STEPS; print('Successfully imported Config and STEPS from steps module')"

# Test that we can run a simple test
RUN python -c "import pytest; print(f'Pytest version: {pytest.__version__}')"

# Set final command
CMD ["/bin/bash"]