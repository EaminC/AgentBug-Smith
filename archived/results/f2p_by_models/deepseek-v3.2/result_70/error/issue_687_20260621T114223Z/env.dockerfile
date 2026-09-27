FROM python:3.9-slim

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

# Install system dependencies needed by MetaGPT (inferred from existing Dockerfile and CI)
RUN apt-get update && apt-get install -y \
    libgomp1 \
    git \
    chromium \
    fonts-ipafont-gothic \
    fonts-wqy-zenhei \
    fonts-thai-tlwg \
    fonts-kacst \
    fonts-freefont-ttf \
    libxss1 \
    --no-install-recommends \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Node.js and mermaid-cli globally (inferred from existing Dockerfile and CI)
RUN apt-get update && apt-get install -y curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g @mermaid-js/mermaid-cli \
    && npm cache clean --force \
    && apt-get purge -y curl && apt-get autoremove -y && apt-get clean && rm -rf /var/lib/apt/lists/*

ENV CHROME_BIN="/usr/bin/chromium" \
    PUPPETEER_SKIP_CHROMIUM_DOWNLOAD="true"

WORKDIR /app

# Copy entire repository (required for external test scripts)
COPY . .

# Install Python dependencies and the project itself (evidence: requirements.txt, setup.py)
RUN python -m pip install --upgrade pip wheel \
    && if [ -f requirements.txt ]; then pip install -r requirements.txt; fi \
    && pip install -e . \
    # Install test dependencies (inferred from extras_require["test"] in setup.py)
    && pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout \
    # Install playwright for web scraping (inferred from requirements.txt and CI)
    && pip install playwright \
    && playwright install --with-deps

# Set PYTHONPATH for multi-package layouts
ENV PYTHONPATH=/app

# Preflight import check
RUN python -c "import metagpt, pytest; print('preflight ok')"

CMD ["/bin/bash"]