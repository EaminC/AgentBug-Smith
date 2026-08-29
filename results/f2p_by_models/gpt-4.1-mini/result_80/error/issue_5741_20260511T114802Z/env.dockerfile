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

# Set Forge API environment variables for OpenAI and Anthropic SDK compatibility
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1" \
    OPENAI_API_KEY="forge-key" \
    ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1" \
    ANTHROPIC_AUTH_TOKEN="forge-key"

WORKDIR /app

# Copy entire project into container
COPY . .

# Upgrade pip, setuptools, wheel
RUN python -m pip install --upgrade pip setuptools wheel

# Install system dependencies needed for building Python packages and tests
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libsqlite3-dev \
    libxml2-dev \
    libxslt1-dev \
    libffi-dev \
    python3-dev \
    build-essential \
    curl \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies if requirements.txt exists, then install the project editable and test deps
RUN if [ -f requirements.txt ]; then \
        pip install -r requirements.txt; \
    fi && \
    pip install -e . && \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm

# Additional commonly needed packages to cover test imports
RUN pip install bs4 mkdocs nbconvert "psycopg[binary]" psycopg_pool numpy langchain_core aiosqlite dataclasses_json sqlite_vec pandas ormsgpack

# Set PYTHONPATH for correct imports in scripts
ENV PYTHONPATH=/app

# Preflight check to verify pytest and local package imports
RUN python -c "import pytest; print('preflight ok')"

CMD ["/bin/bash"]