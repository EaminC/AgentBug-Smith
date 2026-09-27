FROM node:20-slim AS test_builder

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

# Copy entire repository
COPY . .

# Install system dependencies for building native modules and running headless browsers
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    make \
    g++ \
    curl \
    ca-certificates \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libc6 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libgbm1 \
    libgcc1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libstdc++6 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    lsb-release \
    wget \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js dependencies (CRITICAL: Editable installation for JavaScript)
RUN if [ -f "package.json" ]; then \
        npm ci; \
    fi

# Install frontend dependencies and build frontend (if frontend directory exists)
RUN if [ -f "src/frontend/package.json" ]; then \
        cd src/frontend && npm ci; \
    fi

# Install backend dependencies (Python) using uv (Makefile uses uv)
RUN if [ -f "pyproject.toml" ]; then \
        python3 -m pip install --upgrade pip wheel uv; \
        uv sync --frozen; \
        # Install pytest and required testing dependencies (as per Makefile unit_tests target)
        uv pip install pytest pytest-mock pytest-asyncio pytest-cov pytest-xdist pytest-timeout "setuptools<=81.0.0" litellm mem0ai; \
        # CRITICAL: Install the Python package in editable mode
        uv pip install -e .; \
    fi

# Build frontend static files (as per Makefile build_frontend target)
RUN if [ -f "src/frontend/package.json" ]; then \
        cd src/frontend && CI='' npm run build; \
        mkdir -p src/backend/base/langflow/frontend; \
        cp -r src/frontend/build/. src/backend/base/langflow/frontend; \
    fi

# Set PYTHONPATH for multi-package layouts
ENV PYTHONPATH=/app:/app/src/backend:$PYTHONPATH

# Preflight import check to fail fast
RUN python3 -c "import pytest; import langflow; print('preflight ok')"

# Default command to keep container running for test execution
CMD ["/bin/bash"]