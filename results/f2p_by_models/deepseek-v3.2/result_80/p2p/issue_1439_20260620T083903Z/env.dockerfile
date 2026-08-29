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

# Upgrade packaging tools early
RUN python -m pip install --upgrade pip setuptools wheel

# Copy entire repository (including externally injected test scripts)
COPY . .

# Install dependencies and project
# CRITICAL: Unconditional editable installation
RUN pip install -e .

# Install dependencies from requirements files if they exist
RUN if [ -f "requirements.txt" ]; then pip install -r requirements.txt; fi
RUN if [ -f "pyproject.toml" ]; then pip install .[dev] 2>/dev/null || true; fi
RUN if [ -f "pyproject.toml" ]; then pip install .[test] 2>/dev/null || true; fi

# Install test dependencies unconditionally
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Install dev dependencies if uv.lock exists (as per CI) else install from pyproject.toml optional dependencies
RUN if [ -f "uv.lock" ]; then \
        pip install uv && \
        uv sync --dev 2>/dev/null || true; \
    else \
        pip install "crewai[tools]" 2>/dev/null || true; \
        pip install ruff mypy pre-commit mkdocs mkdocstrings mkdocstrings-python mkdocs-material mkdocs-material-extensions pillow cairosvg pytest-vcr pytest-subprocess 2>/dev/null || true; \
    fi

# Set Forge environment variables
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co
ENV ANTHROPIC_AUTH_TOKEN=forge-key

# CRITICAL: Explicit PYTHONPATH for multi-package layouts
# Check for common multi-package layouts and set PYTHONPATH accordingly
RUN if [ -d "src" ]; then \
        echo "src layout detected, setting PYTHONPATH" && \
        export PYTHONPATH=/app/src:$PYTHONPATH; \
    fi && \
    if [ -d "libs" ]; then \
        echo "libs layout detected, adding to PYTHONPATH" && \
        find /app/libs -type d -name "*.egg-info" -prune -o -type f -name "pyproject.toml" -print | while read f; do \
            dir=$(dirname "$f") && \
            echo "Adding $dir to PYTHONPATH" && \
            export PYTHONPATH=$dir:$PYTHONPATH; \
        done; \
    fi && \
    if [ -d "packages" ]; then \
        echo "packages layout detected, adding to PYTHONPATH" && \
        find /app/packages -type d -name "*.egg-info" -prune -o -type f -name "pyproject.toml" -print | while read f; do \
            dir=$(dirname "$f") && \
            echo "Adding $dir to PYTHONPATH" && \
            export PYTHONPATH=$dir:$PYTHONPATH; \
        done; \
    fi

# Final PYTHONPATH setting
ENV PYTHONPATH=/app:$PYTHONPATH

# Preflight import check
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

CMD ["/bin/bash"]