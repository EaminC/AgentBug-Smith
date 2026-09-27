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

# Install system dependencies that are evidenced by the repository (e.g., chromium for mermaid-cli, git)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    git \
    chromium \
    fonts-ipafont-gothic \
    fonts-wqy-zenhei \
    fonts-thai-tlwg \
    fonts-kacst \
    fonts-freefont-ttf \
    libxss1 \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables for puppeteer/chromium (from provided Dockerfile)
ENV CHROME_BIN="/usr/bin/chromium" \
    PUPPETEER_SKIP_CHROMIUM_DOWNLOAD="true"

# Install mermaid-cli globally (as evidenced by setup.py's custom command and original Dockerfile)
RUN npm install -g @mermaid-js/mermaid-cli && npm cache clean --force

WORKDIR /app

# Copy entire repository (as required for test script injection)
COPY . .

# Create workspace directory (as per original Dockerfile)
RUN mkdir -p workspace

# Set PYTHONPATH to include the main source directory
ENV PYTHONPATH=/app:/app/src:/app/metagpt:$PYTHONPATH

# Install Python dependencies using the evidence from requirements.txt and setup.py extras
RUN python -m pip install --upgrade pip wheel && \
    if [ -f requirements.txt ]; then pip install -r requirements.txt; fi && \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai && \
    pip install -e . && \
    if [ -f setup.py ]; then pip install -e .[test]; fi

# Preflight import check to ensure core modules are available
RUN python -c "import metagpt; import pytest; print('preflight ok')"

# Final CMD inferred from entry_points in setup.py: metagpt=metagpt.software_company:app
# However, the test harness expects a bash shell; we keep bash as default.
CMD ["/bin/bash"]