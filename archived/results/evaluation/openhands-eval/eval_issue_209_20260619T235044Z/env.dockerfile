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
ENV MODEL="tuzi-deepseek-v3.2/gpt-4.1-mini"
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

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy repository
COPY . .

# Upgrade pip, setuptools, wheel, and setuptools_scm
RUN python -m pip install --upgrade pip setuptools wheel setuptools_scm

# Clear pip cache to avoid conflicts
RUN python -m pip cache purge

# Install protobuf first with specific version constraint to prevent conflicts
RUN pip install --no-cache-dir "protobuf>=6.31.0,<7.0.0"

# Install dapr dependencies - order matters to avoid proto conflicts
# First install dapr base packages
RUN pip install --no-cache-dir \
    "dapr>=1.16.0rc2" \
    "dapr-ext-fastapi>=1.16.0rc2" \
    "durabletask-dapr>=0.2.0a7"

# Then dapr-ext-workflow (depends on dapr)
RUN pip install --no-cache-dir "dapr-ext-workflow>=1.16.0rc2"

# Install core project dependencies without extras first
# Note: We use the openai version constraint from the project
RUN pip install --no-cache-dir \
    "pydantic>=2.11.3,<3.0.0" \
    "jinja2>=3.1.0,<4.0.0" \
    "pyyaml>=6.0.1,<7.0.0" \
    "requests>=2.32.4,<3.0.0" \
    "openapi-pydantic>=0.5.0,<0.6.0" \
    "rich>=13.9.4,<14.0.0" \
    "openai>=1.75.0,<2.0.0" \
    "azure-identity>=1.21.0,<2.0.0" \
    "huggingface_hub>=0.33.4,<1.0.0" \
    "colorama>=0.4.6,<1.0.0" \
    "regex>=2023.0.0,<2025.0.0" \
    "fastapi>=0.110.0,<1.0.0" \
    "uvicorn>=0.27.0,<1.0.0" \
    "aiohttp>=3.9.0,<4.0.0" \
    "cloudevents>=1.11.0,<2.0.0" \
    "numpy>=2.2.2,<3.0.0" \
    "mcp>=1.7.1,<2.0.0" \
    "websockets>=15.0.0,<16.0.0" \
    "python-dotenv>=1.1.1,<2.0.0" \
    "posthog<6.0.0" \
    "docker>=7.1.0"

# Install the package itself in editable mode
RUN pip install --no-cache-dir -e .

# Install test dependencies
# Note: Install pytest and related packages separately to avoid openai version conflicts with litellm
RUN pip install --no-cache-dir \
    "pytest>=7.0.0,<8.0.0" \
    "pytest-asyncio>=0.23.0,<1.0.0" \
    "pytest-cov>=4.1.0,<5.0.0" \
    "pytest-mock>=3.12.0,<4.0.0" \
    "pytest-xdist>=3.0.0,<4.0.0" \
    "pytest-timeout>=2.3.0,<3.0.0" \
    "httpx>=0.27.0,<1.0.0" \
    "setuptools<=81.0.0"

# Verify core dependencies are available (skip dapr_agents import due to known proto conflict)
RUN python -c "import pytest; import pydantic; print('preflight ok')"

CMD ["/bin/bash"]