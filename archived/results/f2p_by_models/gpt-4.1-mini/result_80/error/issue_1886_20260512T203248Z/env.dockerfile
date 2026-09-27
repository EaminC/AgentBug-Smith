FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tensorblock/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV GITHUB_TOKEN="ghp_key"
ENV TAVILY_API_KEY="tvly-key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tensorblock/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="tensorblock/gpt-4.1-mini"
ENV OPENAI_API_KEY="forge-key"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
# --- end inject ---

# Set working directory
WORKDIR /app

# Set Forge API environment variables for OpenAI-compatibility and Anthropic-compatibility
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1 \
    ANTHROPIC_AUTH_TOKEN=forge-key

# Install system dependencies needed for building Python packages and runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    gcc \
    libxml2-dev \
    libxslt1-dev \
    curl \
    git \
  && rm -rf /var/lib/apt/lists/*

# Copy entire repository
COPY . .

# Upgrade pip and setuptools
RUN python -m pip install --upgrade pip setuptools wheel

# Install requirements if present
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

# Install local project in editable mode unconditionally
RUN pip install -e .

# Install test dependencies unconditionally
RUN pip install pytest pytest-mock pytest-xdist pytest-timeout "setuptools<=81.0.0" litellm

# If multi-package repo detected, install sub-packages editable and set PYTHONPATH accordingly
# (Assuming from repo structure, adjust paths if needed)
RUN if [ -d libs/langgraph ]; then pip install -e libs/langgraph[tests]; fi
RUN if [ -d libs/prebuilt ]; then pip install -e libs/prebuilt; fi
RUN if [ -d libs/sdk-py ]; then pip install -e libs/sdk-py; fi

ENV PYTHONPATH=/app/libs/langgraph:/app/libs/prebuilt:/app/libs/sdk-py:/app

# Preflight test to confirm imports
RUN python -c 'import pkg_resources, pytest, litellm; print("preflight ok")'

CMD ["/bin/bash"]