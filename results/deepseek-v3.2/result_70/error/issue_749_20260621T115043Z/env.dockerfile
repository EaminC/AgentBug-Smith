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

# Set PYTHONPATH for proper module resolution
ENV PYTHONPATH=/app:/app/src:$PYTHONPATH

# Install system dependencies (from evidence in Dockerfile and setup.py)
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
    npm \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install mermaid-cli globally (from evidence in Dockerfile and setup.py)
ENV CHROME_BIN="/usr/bin/chromium" \
    PUPPETEER_SKIP_CHROMIUM_DOWNLOAD="true"
RUN npm install -g @mermaid-js/mermaid-cli && npm cache clean --force

WORKDIR /app

# Copy entire repository
COPY . .

# Install Python dependencies and the project itself
# Use safe conditional installation for requirements.txt
RUN python -m pip install --upgrade pip wheel && \
    if [ -f requirements.txt ]; then pip install -r requirements.txt; fi && \
    pip install -e . && \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Preflight import check
RUN python -c "import metagpt, pytest; print('preflight ok')"

# Default command (from original Dockerfile)
CMD ["sh", "-c", "tail -f /dev/null"]