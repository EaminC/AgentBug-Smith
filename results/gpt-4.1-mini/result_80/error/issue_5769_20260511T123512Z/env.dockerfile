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

# Set environment variables for Forge API compatibility
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1
ENV ANTHROPIC_AUTH_TOKEN=forge-key

# Set argument and default for Forge API key
ARG FORGE_API_KEY=forge-key
ENV FORGE_API_KEY=$FORGE_API_KEY

WORKDIR /app

# Copy the entire repository into the container
COPY . .

# Upgrade pip, setuptools, and wheel
RUN python -m pip install --upgrade pip setuptools wheel

# Install system dependencies needed for some Python packages
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    libsqlite3-dev \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies from requirements.txt if it exists
RUN if [ -f requirements.txt ]; then \
        pip install -r requirements.txt; \
    elif [ -f libs/langgraph/requirements.txt ]; then \
        pip install -r libs/langgraph/requirements.txt; \
    else \
        echo "No requirements.txt found, skipping."; \
    fi

# Install critical test packages and runtime dependencies explicitly mentioned in feedback
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio \
    "setuptools<=81.0.0" litellm nbconvert redis psycopg[binary] \
    psycopg_pool aiosqlite sqlite_vec numpy bs4 mkdocs nbformat

# Install the local langgraph package in editable mode for importability ensuring module path resolution
RUN pip install -e .

# Sanity preflight check for critical packages to catch import errors early
RUN python -c 'import pkg_resources, pytest, redis, nbconvert, psycopg_pool, sqlite_vec, numpy; print("preflight ok")'

# Entrypoint for the container - start bash shell
CMD ["/bin/bash"]