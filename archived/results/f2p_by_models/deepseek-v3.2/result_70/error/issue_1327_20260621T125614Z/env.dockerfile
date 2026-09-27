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

# System dependencies needed for MetaGPT (from provided Dockerfile and setup.py)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libgomp1 \
        git \
        chromium \
        fonts-ipafont-gothic \
        fonts-wqy-zenhei \
        fonts-thai-tlwg \
        fonts-kacst \
        fonts-freefont-ttf \
        libxss1 \
        nodejs \
        npm \
        curl \
        && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set environment variables for puppeteer/chromium (from provided Dockerfile)
ENV CHROME_BIN="/usr/bin/chromium" \
    PUPPETEER_SKIP_CHROMIUM_DOWNLOAD="true"

# Install mermaid-cli globally (from provided Dockerfile and setup.py cmdclass)
RUN npm install -g @mermaid-js/mermaid-cli && \
    npm cache clean --force

# Copy entire repository
COPY . .

# Set PYTHONPATH for multi-package layouts
ENV PYTHONPATH=/app:/app/src:/app/lib:/app/libs:/app/packages:$PYTHONPATH

# Install Python dependencies and MetaGPT itself
RUN python -m pip install --upgrade pip wheel && \
    if [ -f requirements.txt ]; then pip install -r requirements.txt; fi && \
    pip install -e . && \
    # Install test dependencies (from setup.py extras_require["test"] and mandatory pytest packages)
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai pytest-html pytest-timeout connexion[uvicorn] azure-cognitiveservices-speech aioboto3 gradio==3.0.0 grpcio-status pylint==3.0.3 pybrowsers

# Install any sub-packages in editable mode if they exist
RUN if [ -d "libs" ]; then find libs -name "setup.py" -o -name "pyproject.toml" | xargs -I {} dirname {} | xargs -I {} pip install -e {}; fi && \
    if [ -d "packages" ]; then find packages -name "setup.py" -o -name "pyproject.toml" | xargs -I {} dirname {} | xargs -I {} pip install -e {}; fi

# Preflight import check
RUN python -c "import pkg_resources, pytest; print('preflight ok')"

# Default command (as per original Dockerfile, but also allow test harness to override)
CMD ["sh", "-c", "tail -f /dev/null"]