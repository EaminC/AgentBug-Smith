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

# Copy entire repository for test harness injection
COPY . .

# Install system dependencies for open-interpreter (common ones)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        curl \
        wget \
        build-essential \
        && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install wheel
RUN python -m pip install --upgrade pip wheel

# Install project dependencies via poetry (since pyproject.toml and poetry.lock exist? but lock not shown)
# Fallback to pip if poetry.lock missing
RUN if [ -f poetry.lock ]; then \
        pip install poetry && \
        poetry config virtualenvs.create false && \
        poetry install --no-interaction --no-ansi; \
    else \
        pip install -e .; \
    fi

# Install mandatory test dependencies (pytest + pytest plugins)
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Check for requirements.txt and install if present
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

# Check for requirements-dev.txt and install if present
RUN if [ -f requirements-dev.txt ]; then pip install -r requirements-dev.txt; fi

# Check for setup.py and install if present
RUN if [ -f setup.py ]; then pip install -e .; fi

# Set PYTHONPATH to include current directory for local imports
ENV PYTHONPATH=/app:$PYTHONPATH

# Preflight import check to fail fast
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

CMD ["/bin/bash"]