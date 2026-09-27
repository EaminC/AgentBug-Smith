FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tensorblock/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV GITHUB_TOKEN="ghp_key"
ENV TAVILY_API_KEY="tvly_key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tensorblock/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="tensorblock/gpt-4.1-mini"
ENV OPENAI_API_KEY="forge-key"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
# --- end inject ---

# Set working directory
WORKDIR /app

# Set environment variables for Forge API compatibility
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1 \
    ANTHROPIC_AUTH_TOKEN=forge-key

# Install system dependencies needed for Python builds and runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libffi-dev libssl-dev python3-dev curl rustc cargo && \
    rm -rf /var/lib/apt/lists/*

# Upgrade pip, setuptools, and wheel
RUN python -m pip install --upgrade pip setuptools wheel packaging

# Copy all files in the repo
COPY . .

# Install Python dependencies using poetry if poetry.lock exists
RUN if [ -f "poetry.lock" ] && [ -f "pyproject.toml" ]; then \
        pip install poetry && \
        poetry config virtualenvs.create false && \
        poetry install --no-root; \
    elif [ -f "requirements.txt" ]; then \
        pip install -r requirements.txt; \
    fi

# Install the package itself and mandatory test dependencies unconditionally
RUN pip install -e . && pip install pytest pytest-mock pytest-xdist pytest-timeout litellm "setuptools<=81.0.0"

# If the repo contains sub-packages in libs/ or packages/, install them editable and set PYTHONPATH
# (Adjust these paths if your repo structure differs)
RUN if [ -d "libs" ]; then \
        pip install -e libs/langgraph[tests] -e libs/prebuilt -e libs/sdk-py || true; \
    fi

ENV PYTHONPATH=/app/libs/langgraph:/app/libs/prebuilt:/app/libs/sdk-py

# Verify installation with a quick import test
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Default command to run bash shell
CMD ["/bin/bash"]

# branch: python/poetry.lock+pyproject.toml (fallback to requirements.txt if no poetry)