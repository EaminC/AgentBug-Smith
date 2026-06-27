FROM python:3.12-slim AS test_builder

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

# Install system dependencies for Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy entire repository
COPY . .

# Set PYTHONPATH to include common source directories
ENV PYTHONPATH=/app:/app/src:/app/libs:/app/packages:/app/agentscope:/app/tests:$PYTHONPATH

# Install uv if lock file exists, else use pip
RUN python -m pip install --upgrade pip wheel && \
    if [ -f uv.lock ]; then \
        pip install uv && \
        uv sync --dev --all-extras; \
    elif [ -f pyproject.toml ]; then \
        # First install the project in editable mode
        pip install -e . && \
        # Install common testing dependencies
        pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai; \
        # Install optional extras if they exist
        if [ -f "setup.py" ] || [ -f "pyproject.toml" ]; then \
            pip install -e .[tools,embeddings,mem0,fastembed,pandas,openpyxl,pdfplumber,docling,aisuite,agentops] 2>/dev/null || true; \
        fi; \
    else \
        # Look for setup.py as fallback
        if [ -f setup.py ]; then \
            pip install -e . && \
            pip install pytest pytest-mock pytest-asyncio; \
        else \
            echo "No pyproject.toml or setup.py found"; exit 1; \
        fi; \
    fi

# Install any sub-packages in editable mode
RUN find /app -name "setup.py" -o -name "pyproject.toml" | grep -E "(libs|packages|src)" | head -5 | while read f; do \
    dir=$(dirname "$f"); \
    if [ "$dir" != "/app" ]; then \
        echo "Installing sub-package in $dir"; \
        cd "$dir" && pip install -e . 2>/dev/null || true; \
        cd /app; \
    fi; \
done

# Preflight import check to verify core modules
RUN python -c "import sys; sys.path.insert(0, '/app'); import pytest; print('pytest imported successfully')"

# Default command (as per test harness requirement)
CMD ["/bin/bash"]