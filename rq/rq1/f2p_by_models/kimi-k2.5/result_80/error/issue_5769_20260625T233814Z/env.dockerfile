FROM python:3.12-slim

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

WORKDIR /app

# Install system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv (used by the project's Makefile and CI workflows)
RUN pip install uv

# Copy entire repository
COPY . .

# Install mandatory test dependencies as specified
RUN uv pip install --system \
    pytest \
    pytest-mock \
    pytest-asyncio \
    pytest-cov \
    anyio \
    "setuptools<=81.0.0" \
    litellm \
    pytest-xdist \
    pytest-timeout \
    mem0ai

# Install local packages from the monorepo libs/ directories
# Assumption: Repository uses libs/ structure with individual pyproject.toml files
RUN for dir in libs/*/; do \
        if [ -f "${dir}pyproject.toml" ]; then \
            echo "Installing ${dir}..."; \
            cd "${dir}"; \
            if [ -f "uv.lock" ]; then \
                uv sync --frozen --group dev --system || uv pip install --system -e .; \
            else \
                uv pip install --system -e .; \
            fi; \
            cd /app; \
        fi; \
    done

# Fallback for root-level project (if no libs/ structure detected)
RUN if [ -f "pyproject.toml" ] && [ ! -d "libs" ]; then \
        if [ -f "uv.lock" ]; then \
            uv sync --frozen --group dev --system || uv pip install --system -e .; \
        else \
            uv pip install --system -e .; \
        fi; \
    fi

# Ensure root package is installed unconditionally for editable access
RUN if [ -f "pyproject.toml" ]; then \
        pip install -e . || uv pip install --system -e .; \
    fi

# Explicitly configure PYTHONPATH for monorepo structure to resolve cross-namespace imports
ENV PYTHONPATH=/app:/app/libs:/app/libs/agentscope/src:/app/src:${PYTHONPATH}

# Verify installation
RUN python -c "import sys; print('Python path:', sys.path)"