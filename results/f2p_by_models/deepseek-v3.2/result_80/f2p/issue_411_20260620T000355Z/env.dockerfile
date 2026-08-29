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

# Set environment variables for Forge
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co
ENV ANTHROPIC_AUTH_TOKEN=forge-key

# Install system dependencies for building packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Upgrade packaging tools early
RUN python -m pip install --upgrade pip setuptools wheel

# Copy entire repository (including any externally injected test scripts)
COPY . .

# Detect src/ layout to decide editable install
RUN if [ -d "src" ] || grep -Rq "^\s*from src\.|^\s*import src\." tests 2>/dev/null; then \
        echo "Detected src/ layout or src imports - skipping editable install, setting PYTHONPATH" && \
        export PYTHONPATH=/app; \
    else \
        echo "No src/ layout detected - will perform editable install"; \
    fi

# Install dependencies based on available files
RUN if [ -f "requirements.txt" ]; then \
        pip install -r requirements.txt; \
    fi && \
    if [ -f "pyproject.toml" ] && [ -f "poetry.lock" ]; then \
        pip install poetry && \
        poetry config virtualenvs.create false && \
        poetry install --no-interaction --no-ansi; \
    elif [ -f "pyproject.toml" ]; then \
        # Assumption: no lockfile; install with pip
        pip install -e .; \
    else \
        pip install -e .; \
    fi

# Install mandatory test dependencies (unconditionally)
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Install optional extras if needed (based on setup.py)
RUN pip install -e .[full]

# Preflight check to ensure core modules are importable
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

CMD ["/bin/bash"]