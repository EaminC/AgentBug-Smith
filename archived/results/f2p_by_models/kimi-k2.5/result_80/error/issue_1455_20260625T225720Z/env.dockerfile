FROM python:3.9-slim

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

# Install system dependencies and Node.js (required for mermaid-cli and frontend tooling)
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
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables for Chromium/Puppeteer (required by mermaid and playwright)
ENV CHROME_BIN="/usr/bin/chromium" \
    PUPPETEER_SKIP_CHROMIUM_DOWNLOAD="true"

# Install Mermaid CLI globally (used for diagram generation)
RUN npm install -g @mermaid-js/mermaid-cli && npm cache clean --force

WORKDIR /app

# Copy entire repository (required for test script injection)
COPY . .

# Install Python dependencies: requirements.txt exists (Branch 1)
# Includes mandatory testing frameworks per spec: pytest, pytest-mock, setuptools<=81.0.0, litellm, etc.
# CRITICAL: Safe file operations and unconditional editable install for monorepo support
RUN python -m pip install --upgrade pip wheel && \
    if [ -f requirements.txt ]; then pip install -r requirements.txt; fi && \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# CRITICAL: Editable installation of local package and potential sub-packages (monorepo support)
# Install root package unconditionally
RUN pip install -e .

# Handle monorepo structures: check for and install sub-packages if they exist
RUN if [ -d libs ]; then \
        for dir in libs/*/; do \
            if [ -f "${dir}setup.py" ] || [ -f "${dir}pyproject.toml" ]; then \
                pip install -e "${dir}"; \
            fi; \
        done; \
    fi && \
    if [ -d packages ]; then \
        for dir in packages/*/; do \
            if [ -f "${dir}setup.py" ] || [ -f "${dir}pyproject.toml" ]; then \
                pip install -e "${dir}"; \
            fi; \
        done; \
    fi

# CRITICAL: Explicitly configure PYTHONPATH for monorepo layouts
ENV PYTHONPATH=/app:/app/src:/app/libs:/app/packages:${PYTHONPATH}

# Install Playwright browsers and system dependencies (required for web scraping tests)
RUN playwright install --with-deps

# Preflight verification to ensure core tooling is importable and package is installed
RUN python -c 'import pkg_resources, pytest; print("preflight ok")' && \
    python -c 'import sys; print("PYTHONPATH:", sys.path)'

CMD ["/bin/bash"]