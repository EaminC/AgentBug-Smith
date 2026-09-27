# Use Python 3.11 slim for better compatibility and smaller size
FROM python:3.11-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tuzi-kimi-k2.5/kimi-k2.5"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tuzi-kimi-k2.5/kimi-k2.5"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi-kimi-k2.5/kimi-k2.5"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

# Set working directory
WORKDIR /app

# Environment variables for Forge API
ENV FORGE_API_KEY="forge-key" \
    FORGE_BASE_URL="https://api.forge.tensorblock.co/v1" \
    OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1" \
    OPENAI_API_KEY="forge-key" \
    ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1" \
    ANTHROPIC_AUTH_TOKEN="forge-key" \
    ANTHROPIC_MODEL="tuzi-kimi-k2.5/kimi-k2.5" \
    ANTHROPIC_SMALL_FAST_MODEL="tuzi-kimi-k2.5/kimi-k2.5" \
    MODEL="tuzi-kimi-k2.5/kimi-k2.5" \
    TAVILY_API_KEY="tvly-dev-key" \
    GITHUB_TOKEN="ghp_key" \
    PYTHONPATH="/app:/app/benchmark:/app/forge:/app/autogpt" \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies in a single layer with cleanup
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    gcc \
    build-essential \
    libpq-dev \
    libxml2-dev \
    libxslt1-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire repository
COPY . .

# Create virtual environment and install dependencies
# Using venv avoids PEP 668 issues
RUN python3 -m venv /venv && \
    /venv/bin/pip install --upgrade pip wheel setuptools && \
    /venv/bin/pip install \
        pytest pytest-mock pytest-asyncio pytest-cov pytest-timeout pytest-xdist \
        litellm mem0ai requests anthropic openai pydantic fastapi click colorama \
        beautifulsoup4 pyyaml tenacity tiktoken numpy pillow jinja2 sqlalchemy \
        uvicorn gitpython docker duckduckgo-search groq chromadb aiohttp \
        boto3 selenium webdriver-manager pexpect psutil pandas matplotlib \
        httpx toml tabulate python-dotenv python-multipart pypdf \
        python-docx orjson inflection distro ftfy gTTS \
        openapi-python-client sentry-sdk jsonschema charset-normalizer \
    && \
    if [ -f "benchmark/setup.py" ] || [ -f "benchmark/pyproject.toml" ]; then \
        /venv/bin/pip install -e ./benchmark || true; \
    fi && \
    if [ -f "forge/setup.py" ] || [ -f "forge/pyproject.toml" ]; then \
        /venv/bin/pip install -e ./forge || true; \
    fi && \
    if [ -f "autogpt/setup.py" ] || [ -f "autogpt/pyproject.toml" ]; then \
        /venv/bin/pip install -e ./autogpt || true; \
    fi && \
    find /venv -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true && \
    find /venv -type f -name "*.pyc" -delete 2>/dev/null || true && \
    rm -rf /root/.cache/pip /tmp/* /var/tmp/*

# Add venv to PATH
ENV PATH="/venv/bin:$PATH"

# Cleanup build dependencies to save space
RUN apt-get purge -y --auto-remove gcc build-essential python3-dev 2>/dev/null || true && \
    apt-get autoremove -y 2>/dev/null || true && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/* /tmp/* /var/tmp/*

# Pre-flight check
RUN python -c "import pytest; import openai; import anthropic; print('preflight ok')"

CMD ["/bin/bash"]
