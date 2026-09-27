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

# Install system dependencies for MetaGPT (based on evidence from README and Dockerfile)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    chromium \
    fonts-ipafont-gothic \
    fonts-wqy-zenhei \
    fonts-thai-tlwg \
    fonts-kacst \
    fonts-freefont-ttf \
    libxss1 \
    libgomp1 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Node.js and mermaid-cli (based on evidence from README and Dockerfile)
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    npm install -g @mermaid-js/mermaid-cli && \
    npm cache clean --force

# Set environment variables for Chromium and puppeteer
ENV CHROME_BIN="/usr/bin/chromium" \
    PUPPETEER_SKIP_CHROMIUM_DOWNLOAD="true"

WORKDIR /app

# Copy entire repository
COPY . .

# Install Python dependencies and the project itself
RUN python -m pip install --upgrade pip wheel && \
    # Install core dependencies from requirements.txt (with safety check)
    if [ -f requirements.txt ]; then pip install -r requirements.txt; fi && \
    # Install the project in editable mode
    pip install -e . && \
    # Install test dependencies
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Set PYTHONPATH to include the project root
ENV PYTHONPATH=/app:$PYTHONPATH

# Preflight import check to ensure core modules are accessible
RUN python -c "import metagpt; import pytest; print('preflight ok')"

# Default command (inferred from setup.py entry_points: "metagpt=metagpt.software_company:app")
CMD ["metagpt"]