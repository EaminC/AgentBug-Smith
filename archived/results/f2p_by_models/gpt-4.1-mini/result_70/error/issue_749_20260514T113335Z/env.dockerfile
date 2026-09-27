FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tensorblock/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV GITHUB_TOKEN="ghp_key"
ENV TAVILY_API_KEY="tvly_key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tensorblock/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="tensorblock/gpt-4.1-mini"
ENV OPENAI_API_KEY="forge-key"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
# --- end inject ---

# Set environment variables for Forge API compatibility
ENV FORGE_API_KEY="forge-key" \
    OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1" \
    OPENAI_API_KEY="forge-key" \
    ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1" \
    ANTHROPIC_AUTH_TOKEN="forge-key" \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Copy entire repository contents
COPY . .

# Install system dependencies required for Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    build-essential \
    python3-dev \
 && rm -rf /var/lib/apt/lists/*

# Upgrade pip, setuptools, wheel to latest compatible versions
RUN python -m pip install --upgrade pip setuptools wheel

# Fix potential faiss package name typo in requirements.txt
RUN if [ -f requirements.txt ]; then \
    sed -i 's/faiss_cpu==1.7.4/faiss-cpu==1.13.2/' requirements.txt || true; \
  fi

# Install dependencies and package, avoiding numpy build error on Python 3.12 by using --pre for pre-releases
# Also install required test dependencies
RUN if [ -f requirements.txt ]; then \
      pip install --no-cache-dir --pre -r requirements.txt; \
    fi && \
    pip install --no-cache-dir -e . pytest pytest-mock pytest-xdist pytest-timeout pytest-asyncio pytest-cov anyio litellm

# Preflight test - verify pip and pytest install and work
RUN python -c "import pkg_resources, pytest; print('preflight ok')"

CMD ["/bin/bash"]