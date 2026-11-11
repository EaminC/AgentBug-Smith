FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="openrouter2/openai/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="openrouter2/openai/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="openrouter2/openai/gpt-4.1-mini"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

# Set Forge API environment variables for OpenAI and Anthropic SDK compatibility
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co
ENV ANTHROPIC_AUTH_TOKEN=forge-key

# Also set the key and base url envs explicitly to avoid missing environment errors
ENV FORGE_API_KEY=forge-key
ENV FORGE_BASE_URL=https://api.forge.tensorblock.co/v1

# Set working directory
WORKDIR /app

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc build-essential libpq-dev libxml2-dev libxslt1-dev python3-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip, setuptools, wheel
RUN python -m pip install --upgrade pip setuptools wheel

# Copy entire repository into container
COPY . .

# Install all packages in editable mode so dependencies are resolved and packages available to tests
RUN pip install -e ./lib/crewai ./lib/crewai-tools ./lib/devtools \
    && pip install pytest pytest-asyncio pytest-mock pytest-subprocess pytest-xdist pytest-timeout pytest-recording pytest-randomly pytest-split vcrpy \
    types-requests types-pyyaml types-regex types-appdirs

# Set PYTHONPATH to include source directories for proper imports in testing
ENV PYTHONPATH=/app/lib/crewai/src:/app/lib/crewai-tools/src:/app/lib/devtools/src

# Default command to open bash shell
CMD ["/bin/bash"]

# branch: python/pyproject.toml multi-package editable install with Forge API env vars and pytest deps
