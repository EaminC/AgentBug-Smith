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

# System dependencies for MetaGPT
RUN apt-get update && apt-get install -y --no-install-recommends \
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
    && rm -rf /var/lib/apt/lists/*

# Node.js for mermaid-cli (required by MetaGPT)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g @mermaid-js/mermaid-cli \
    && npm cache clean --force \
    && rm -rf /var/lib/apt/lists/*

ENV CHROME_BIN="/usr/bin/chromium" \
    PUPPETEER_SKIP_CHROMIUM_DOWNLOAD="true" \
    PYTHONPATH="/app"

WORKDIR /app

# Copy entire repository
COPY . .

# Install Python dependencies and MetaGPT itself
RUN python -m pip install --upgrade pip wheel && \
    if [ -f requirements.txt ]; then \
        pip install -r requirements.txt; \
    fi && \
    # Install test dependencies (mandatory for Python projects)
    pip install pytest pytest-mock pytest-asyncio pytest-cov pytest-xdist pytest-timeout "setuptools<=81.0.0" litellm mem0ai && \
    # Install the package in development mode (editable)
    pip install -e .[test]

# Preflight import check
RUN python -c "import metagpt, pytest; print('Preflight import successful')"

# Default command (as per original Dockerfile, but using bash)
CMD ["/bin/bash"]