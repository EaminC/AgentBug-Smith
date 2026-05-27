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

# Set environment variables for Forge API compatibility (OpenAI and Anthropic SDKs)
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1 \
    ANTHROPIC_AUTH_TOKEN=forge-key

WORKDIR /app

# Copy entire repository into container
COPY . .

# Install system dependencies needed for Python builds and extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip, setuptools, wheel
RUN python -m pip install --upgrade pip setuptools wheel

# Install Python dependencies if requirements.txt exists
RUN if [ -f "requirements.txt" ]; then pip install -r requirements.txt; fi

# Install the project libraries in editable mode (unconditionally)
RUN pip install -e .

# Install test framework dependencies and other common tools
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov pytest-xdist pytest-timeout anyio "setuptools<=81.0.0" litellm

# Install extra dependencies needed by the project noted from prior observation
RUN pip install beautifulsoup4 mkdocs nbformat psycopg[binary] aiosqlite dataclasses_json redis

# Preflight verify core packages load correctly
RUN python -c 'import pkg_resources, pytest, redis, psycopg, aiosqlite, dataclasses_json; print("preflight ok")'

CMD ["/bin/bash"]