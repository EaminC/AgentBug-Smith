# AutoGPT Environment Dockerfile - Single-stage space-optimized build
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

WORKDIR /app

# Install system dependencies and build tools in one layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libxml2-dev \
    libxslt1-dev \
    git \
    ca-certificates \
    libxml2 \
    libxslt1.1 \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/*

# Upgrade pip and wheel
RUN pip install --no-cache-dir --upgrade pip wheel "setuptools<=81.0.0"

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies from requirements.txt (excluding problematic lines)
RUN grep -v "^#" requirements.txt | grep -v "^$" | grep -v "pinecone-client" | \
    pip install --no-cache-dir -r /dev/stdin || true

# Install additional packages manually
RUN pip install --no-cache-dir \
    beautifulsoup4>=4.12.2 \
    colorama==0.4.6 \
    distro==1.8.0 \
    openai==0.27.2 \
    python-dotenv==1.0.0 \
    pyyaml==6.0 \
    PyPDF2 \
    python-docx \
    markdown \
    pylatexenc \
    readability-lxml==0.8.1 \
    requests \
    tiktoken==0.3.3 \
    gTTS==2.3.1 \
    duckduckgo-search==3.0.2 \
    google-api-python-client \
    redis \
    orjson==3.8.10 \
    Pillow \
    jsonschema \
    click \
    charset-normalizer>=3.1.0 \
    spacy>=3.0.0,<4.0.0 \
    prompt_toolkit>=3.0.38 \
    pydantic \
    fastapi \
    uvicorn \
    numpy \
    gitpython==3.1.31 \
    openapi-python-client==0.13.4 \
    mkdocs \
    pymdown-extensions \
    https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.5.0/en_core_web_sm-3.5.0-py3-none-any.whl \
    git+https://github.com/Significant-Gravitas/Auto-GPT-Plugin-Template@0.1.0

# Install test dependencies
RUN pip install --no-cache-dir \
    pytest \
    asynctest \
    pytest-asyncio \
    pytest-benchmark \
    pytest-cov \
    pytest-integration \
    pytest-mock \
    pytest-xdist \
    pytest-timeout \
    litellm \
    mem0ai \
    vcrpy \
    pytest-recording \
    git+https://github.com/Significant-Gravitas/vcrpy.git@master

# Copy project source
COPY . .

# Install the project itself
RUN pip install -e . --no-cache-dir

# Environment variables for Forge API
ENV FORGE_API_KEY="forge-key" \
    FORGE_BASE_URL="https://api.forge.tensorblock.co/v1" \
    MODEL="tuzi-kimi-k2.5/kimi-k2.5" \
    AI_TEMPERATURE="0.7" \
    AI_MAX_TOKENS="1000" \
    AI_TOP_P="1" \
    AI_FREQUENCY_PENALTY="0" \
    AI_PRESENCE_PENALTY="0" \
    OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1" \
    OPENAI_API_KEY="forge-key" \
    ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1" \
    ANTHROPIC_AUTH_TOKEN="forge-key" \
    ANTHROPIC_MODEL="tuzi-kimi-k2.5/kimi-k2.5" \
    ANTHROPIC_SMALL_FAST_MODEL="tuzi-kimi-k2.5/kimi-k2.5" \
    TAVILY_API_KEY="tvly-dev-key" \
    GITHUB_TOKEN="ghp_key" \
    PYTHONDONTWRITEBYTECODE="1" \
    PYTHONUNBUFFERED="1" \
    PIP_NO_CACHE_DIR="1" \
    PIP_DISABLE_PIP_VERSION_CHECK="1" \
    PYTHONPATH="/app"

# Preflight check
RUN python -c "import pytest, openai, requests, yaml, spacy; print('Preflight checks passed')"

CMD ["/bin/bash"]
