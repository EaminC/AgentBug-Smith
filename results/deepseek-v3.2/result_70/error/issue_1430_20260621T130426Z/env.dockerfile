FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

WORKDIR /app

# Install system dependencies needed by MetaGPT
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        libgomp1 \
        chromium \
        fonts-ipafont-gothic \
        fonts-wqy-zenhei \
        fonts-thai-tlwg \
        fonts-kacst \
        fonts-freefont-ttf \
        libxss1 \
        curl \
        ca-certificates \
        && rm -rf /var/lib/apt/lists/*

# Install Node.js and mermaid-cli globally
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g @mermaid-js/mermaid-cli && \
    npm cache clean --force

# Set environment variables for Chromium and puppeteer
ENV CHROME_BIN=/usr/bin/chromium \
    PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true \
    PYTHONPATH=/app

# Copy entire repository
COPY . .

# Install Python dependencies with safe file operations
RUN python -m pip install --upgrade pip wheel setuptools && \
    if [ -f requirements.txt ]; then pip install -r requirements.txt; fi && \
    if [ -f requirements-dev.txt ]; then pip install -r requirements-dev.txt; fi && \
    pip install -e . && \
    # Install test dependencies
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio pytest-xdist pytest-timeout

# Preflight check to ensure core modules can be imported
RUN python -c "import metagpt; import pytest; print('preflight ok')"

CMD ["/bin/bash"]