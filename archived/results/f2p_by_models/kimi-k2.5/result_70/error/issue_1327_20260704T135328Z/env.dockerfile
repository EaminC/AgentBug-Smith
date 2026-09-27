FROM python:3.12-slim-bookworm

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

# ============================================================================
# FORGE API CONFIGURATION - OpenAI/Anthropic Compatibility
# ============================================================================
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tuzi-kimi-k2.5/kimi-k2.5"
ENV AI_TEMPERATURE="0.7"
ENV AI_MAX_TOKENS="1000"
ENV AI_TOP_P="1"
ENV AI_FREQUENCY_PENALTY="0"
ENV AI_PRESENCE_PENALTY="0"

# OpenAI SDK compatibility
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"

# Anthropic SDK compatibility
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tuzi-kimi-k2.5/kimi-k2.5"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi-kimi-k2.5/kimi-k2.5"

# Other API keys
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"

# Proxy settings




# Chromium settings
ENV CHROME_BIN="/usr/bin/chromium"
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD="true"

# Python settings - avoid PEP 668 issues
ENV PIP_BREAK_SYSTEM_PACKAGES=1
ENV PYTHONPATH=/app

# ============================================================================
# SYSTEM DEPENDENCIES - Install only essential packages
# ============================================================================
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    git \
    chromium \
    fonts-ipafont-gothic \
    fonts-wqy-zenhei \
    fonts-thai-tlwg \
    fonts-freefont-ttf \
    fontconfig \
    libxss1 \
    curl \
    ca-certificates \
    libxml2-dev \
    libxslt1-dev \
    python3-dev \
    gcc \
    g++ \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20 separately
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    npm cache clean --force

# Install mermaid-cli globally
RUN npm install -g @mermaid-js/mermaid-cli && npm cache clean --force

# ============================================================================
# PYTHON ENVIRONMENT SETUP
# ============================================================================
# Upgrade pip and install core tools
RUN pip install --no-cache-dir --upgrade pip wheel setuptools==65.6.3

# ============================================================================
# COPY AND INSTALL PYTHON DEPENDENCIES
# ============================================================================
COPY requirements.txt .

# Fix faiss-cpu package name and install dependencies
RUN sed -i 's/faiss_cpu==1.7.4/faiss-cpu>=1.7.4,<1.8.0/' requirements.txt && \
    pip install --no-cache-dir -r requirements.txt

# Install test dependencies
RUN pip install --no-cache-dir \
    pytest \
    pytest-asyncio \
    pytest-cov \
    pytest-mock \
    pytest-html \
    pytest-xdist \
    pytest-timeout \
    "setuptools<=81.0.0" \
    litellm \
    mem0ai \
    anyio \
    httpx

# ============================================================================
# COPY REPOSITORY
# ============================================================================
COPY . .

# Install the metagpt package
RUN pip install --no-cache-dir -e .

# ============================================================================
# PREFLIGHT CHECK - Minimal verification
# ============================================================================
RUN python -c "import sys; print(f'Python {sys.version}')" && \
    python -c "import metagpt; print('MetaGPT import OK')" && \
    python -c "import pytest; print('pytest OK')" && \
    python -c "import openai; print('openai OK')" && \
    python -c "import anthropic; print('anthropic OK')"

# ============================================================================
# FINAL CONFIGURATION
# ============================================================================
WORKDIR /app

# Default command must be /bin/bash for the testing environment
CMD ["/bin/bash"]
