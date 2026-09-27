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

# Install system dependencies (inferred from existing Dockerfile and GitHub workflows)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    chromium \
    fonts-ipafont-gothic \
    fonts-wqy-zenhei \
    fonts-thai-tlwg \
    fonts-kacst \
    fonts-freefont-ttf \
    libxss1 \
    libgomp1 \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js and npm for mermaid-cli (inferred from existing Dockerfile and GitHub workflows)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl gnupg && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Install mermaid-cli globally (inferred from existing Dockerfile and GitHub workflows)
RUN npm install -g @mermaid-js/mermaid-cli && \
    npm cache clean --force

# Set environment variables for chromium/puppeteer (inferred from existing Dockerfile)
ENV CHROME_BIN="/usr/bin/chromium" \
    PUPPETEER_SKIP_CHROMIUM_DOWNLOAD="true"

# Copy entire repository
COPY . .

# Set PYTHONPATH for multi-package layouts
ENV PYTHONPATH=/app:/app/src:/app/lib:/app/libs:$PYTHONPATH

# Install Python dependencies, project, and test tooling
RUN python -m pip install --upgrade pip wheel && \
    # Install requirements if file exists
    if [ -f requirements.txt ]; then pip install -r requirements.txt; fi && \
    # Install project in editable mode
    pip install -e . && \
    # Install test dependencies if test extras exist
    if [ -f setup.py ] || [ -f pyproject.toml ]; then \
        pip install -e .[test] 2>/dev/null || pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai; \
    else \
        pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai; \
    fi

# Install playwright for web scraping tests (inferred from GitHub workflows)
RUN playwright install --with-deps

# Preflight import check
RUN python -c "import metagpt, pytest; print('preflight ok')"

CMD ["/bin/bash"]