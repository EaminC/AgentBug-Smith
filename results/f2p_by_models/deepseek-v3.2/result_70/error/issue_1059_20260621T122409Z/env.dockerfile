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

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    chromium \
    fonts-ipafont-gothic \
    fonts-wqy-zenhei \
    fonts-thai-tlwg \
    fonts-kacst \
    fonts-freefont-ttf \
    libxss1 \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables for chromium
ENV CHROME_BIN=/usr/bin/chromium \
    PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true

# Set working directory
WORKDIR /app

# Copy entire repository
COPY . .

# Set PYTHONPATH for multi-package support
ENV PYTHONPATH=/app:/app/src:/app/lib:/app/libs:/app/packages:$PYTHONPATH

# Install Node.js dependencies (mermaid-cli) if package.json exists
RUN if [ -f package.json ]; then \
        apt-get update && apt-get install -y --no-install-recommends nodejs npm && \
        npm install -g @mermaid-js/mermaid-cli && \
        npm cache clean --force && \
        apt-get purge -y --auto-remove nodejs npm && rm -rf /var/lib/apt/lists/*; \
    fi

# Install Python dependencies
RUN python -m pip install --upgrade pip wheel && \
    if [ -f requirements.txt ]; then \
        pip install -r requirements.txt; \
    fi && \
    # Install the package in development mode
    pip install -e . && \
    # Install test dependencies
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai \
        pytest-html connexion[uvicorn] azure-cognitiveservices-speech aioboto3 gradio grpcio-status pylint pybrowsers \
        selenium webdriver_manager google-api-python-client duckduckgo-search paddlepaddle paddleocr tabulate \
        pyppeteer chromadb

# Install any sub-packages in editable mode
RUN find /app -name "setup.py" -o -name "pyproject.toml" | grep -E "(libs|packages|src)" | head -5 | while read f; do \
        dir=$(dirname "$f"); \
        echo "Installing package from $dir"; \
        cd "$dir" && pip install -e . || echo "Failed to install from $dir"; \
        cd /app; \
    done

# Preflight import check
RUN python -c 'import pkg_resources, pytest; print("preflight ok")' && \
    python -c "import sys; print('Python path:', sys.path)"

CMD ["/bin/bash"]