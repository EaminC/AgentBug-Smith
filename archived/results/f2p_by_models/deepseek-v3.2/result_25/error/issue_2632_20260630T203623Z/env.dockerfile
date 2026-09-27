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

# Install system dependencies required by some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy entire repository
COPY . .

# Set PYTHONPATH for monorepo support - include common source directories
ENV PYTHONPATH=/app:/app/src:/app/libs:/app/packages:/app/agentscope:/app/tests:$PYTHONPATH

# Install uv for dependency management (consistent with project CI)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    export PATH="/root/.cargo/bin:$PATH" && \
    uv --version

# Install project dependencies using uv (preferred) or pip fallback
RUN if [ -f pyproject.toml ]; then \
        export PATH="/root/.cargo/bin:$PATH" && \
        if command -v uv > /dev/null 2>&1; then \
            uv sync --dev --all-extras; \
        else \
            pip install --upgrade pip wheel setuptools && \
            pip install -e .[dev,tools,embeddings,agentops,fastembed,pdfplumber,pandas,openpyxl,mem0,docling,aisuite]; \
        fi; \
    else \
        echo "No pyproject.toml found, installing test dependencies only"; \
        pip install --upgrade pip wheel setuptools; \
    fi

# Install core test dependencies (ensure coverage with conditional checks)
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio pytest-xdist pytest-timeout

# CRITICAL: Install the local package in editable mode unconditionally
RUN if [ -f setup.py ]; then \
        pip install -e .; \
    elif [ -f pyproject.toml ]; then \
        pip install -e .; \
    else \
        echo "No setup.py or pyproject.toml found for editable install"; \
    fi

# Verify installation and imports
RUN python -c "import sys; print('Python path:', sys.path)" && \
    python -c "import pytest; print('Pytest version:', pytest.__version__)" && \
    echo "Environment verification complete"

CMD ["/bin/bash"]