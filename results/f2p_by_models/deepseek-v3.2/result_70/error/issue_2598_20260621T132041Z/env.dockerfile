FROM python:3.10-slim AS test_builder

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

# Install Node.js for frontend
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy entire repository
COPY . .

# Install Poetry
RUN pip install poetry

# Install Python dependencies first
RUN if [ -f "pyproject.toml" ]; then \
        poetry config virtualenvs.create false && \
        poetry install --with dev; \
    elif [ -f "requirements.txt" ]; then \
        pip install -r requirements.txt; \
    elif [ -f "requirements-dev.txt" ]; then \
        pip install -r requirements-dev.txt; \
    fi

# Install the project in editable mode if setup.py or pyproject.toml exists
RUN if [ -f "setup.py" ]; then \
        pip install -e .; \
    elif [ -f "pyproject.toml" ]; then \
        pip install -e .; \
    fi

# Set PYTHONPATH for monorepo structure
ENV PYTHONPATH=/app:/app/src:/app/lib:/app/libs:/app/packages:$PYTHONPATH

# Install frontend dependencies if they exist
RUN if [ -f "src/frontend/package.json" ]; then \
        cd src/frontend && npm ci; \
    elif [ -f "package.json" ]; then \
        npm ci; \
    else \
        echo "No package.json found, skipping Node.js installation"; \
    fi

# Install Playwright browsers if playwright is a dev dependency
RUN if [ -f "src/frontend/package.json" ] && grep -q '"@playwright/test"' src/frontend/package.json; then \
        cd src/frontend && npx playwright install --with-deps; \
        npx playwright install-deps; \
    elif [ -f "package.json" ] && grep -q '"@playwright/test"' package.json; then \
        npx playwright install --with-deps; \
        npx playwright install-deps; \
    fi

# Preflight check
RUN python3 -c "import sys; print('Python version:', sys.version); print('PYTHONPATH:', sys.path)"

CMD ["/bin/bash"]