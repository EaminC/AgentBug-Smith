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

# Install system dependencies including git for setuptools_scm and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    gcc \
    libffi-dev \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy entire repository
COPY . .

# Upgrade pip, setuptools, and wheel
RUN python -m pip install --upgrade pip setuptools wheel

# Install local project in editable mode unconditionally
RUN pip install -e .

# Install test dependencies unconditionally
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout

# If requirements.txt exists, install requirements (safe conditional)
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

# Validate installation
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Set Forge API environment variables to use Forge instead of OpenAI
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co \
    ANTHROPIC_AUTH_TOKEN=forge-key

# Set locale and unbuffered mode for Python
ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONUNBUFFERED=1

# Set PYTHONPATH to /app to ensure local imports work correctly
ENV PYTHONPATH=/app

# Default cmd to keep container alive in bash shell
CMD ["/bin/bash"]