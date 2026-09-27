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

# Set working directory
WORKDIR /app

# Install system dependencies for building native modules and Python support
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    python3 \
    python3-pip \
    python3-venv \
    make \
    g++ \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Check for package.json in root (JavaScript project)
RUN if [ -f package.json ]; then \
    echo "Found root package.json, installing JavaScript dependencies"; \
    if [ -f package-lock.json ]; then \
        npm ci; \
    else \
        npm install; \
    fi \
fi

# Check for Python dependencies if pyproject.toml exists
RUN if [ -f pyproject.toml ]; then \
    echo "Found pyproject.toml, installing Python dependencies"; \
    pip3 install --upgrade pip; \
    pip3 install poetry; \
    poetry config virtualenvs.create false; \
    poetry install --no-interaction --no-ansi; \
elif [ -f requirements.txt ]; then \
    echo "Found requirements.txt, installing Python dependencies"; \
    pip3 install --upgrade pip; \
    pip3 install -r requirements.txt; \
fi

# Check for frontend package.json and install if exists
RUN if [ -f src/frontend/package.json ]; then \
    echo "Found frontend package.json, installing frontend dependencies"; \
    cd src/frontend && \
    if [ -f package-lock.json ]; then \
        npm ci; \
    else \
        npm install; \
    fi && \
    cd /app; \
fi

# Install Playwright if frontend exists and has playwright dependency
RUN if [ -f src/frontend/package.json ] && grep -q "playwright" src/frontend/package.json; then \
    echo "Installing Playwright browsers"; \
    cd src/frontend && \
    npx playwright install --with-deps chromium; \
    cd /app; \
fi

# Install the local JavaScript project if it exists
RUN if [ -f package.json ]; then \
    echo "Installing local JavaScript project"; \
    npm install .; \
fi

# Set up Python environment if Python project exists
RUN if [ -f pyproject.toml ] || [ -f setup.py ] || [ -f requirements.txt ]; then \
    echo "Setting up Python environment"; \
    if [ -f setup.py ]; then \
        pip3 install -e .; \
    fi; \
    # Set PYTHONPATH to include current directory
    echo "export PYTHONPATH=/app:\$PYTHONPATH" >> ~/.bashrc; \
fi

# Verify installations
RUN echo "=== Environment Verification ===" && \
    node --version && \
    npm --version && \
    python3 --version && \
    pip3 --version

# Final command (as required by test harness)
CMD ["/bin/bash"]