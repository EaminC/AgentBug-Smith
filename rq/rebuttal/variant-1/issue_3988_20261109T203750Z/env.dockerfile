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

# Additional environment variables
ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/lib/crewai/src:/app/lib/crewai-tools/src

WORKDIR /app

# Install system build dependencies required for cryptography and python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libffi-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    python3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy entire repo into container
COPY . .

# Upgrade pip and setuptools
RUN python -m pip install --upgrade pip setuptools wheel

# Install base dependencies and install both packages in editable mode
RUN if [ -f "requirements.txt" ]; then pip install -r requirements.txt; fi && \
    pip install -e ./lib/crewai && \
    pip install -e ./lib/crewai-tools && \
    pip install cryptography pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm

# Verify installation
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Start bash for testing environment compatibility
CMD ["/bin/bash"]

# branch: python project with pyproject.toml, editable install, cryptography added, Forge API env vars, explicit test deps, src layout
