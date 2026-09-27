FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tensorblock/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV GITHUB_TOKEN="ghp_key"
ENV TAVILY_API_KEY="tvly-key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tensorblock/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="tensorblock/gpt-4.1-mini"
ENV OPENAI_API_KEY="forge-key"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
# --- end inject ---

# Set environment variables for Forge API compatibility
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1 \
    ANTHROPIC_AUTH_TOKEN=forge-key

WORKDIR /app

# Copy the entire repository into the container
COPY . .

# Install system dependencies needed for building Python packages
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends gcc python3-dev build-essential; \
    rm -rf /var/lib/apt/lists/*;

# Upgrade pip, setuptools, wheel
RUN python -m pip install --upgrade pip setuptools wheel

# Install Python dependencies and package, then add testing dependencies
RUN set -eux; \
    if [ -f "requirements.txt" ]; then \
        pip install -r requirements.txt; \
    elif [ -f "poetry.lock" ] && [ -f "pyproject.toml" ]; then \
        pip install poetry; \
        poetry config virtualenvs.create false; \
        poetry install --no-interaction --no-ansi; \
    elif [ -f "pyproject.toml" ]; then \
        pip install -e .; \
    else \
        echo "No Python dependency file found, skipping install"; \
    fi; \
    pip install -e .; \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm

# Preflight import test to verify installation
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Default command to open bash shell
CMD ["/bin/bash"]

# branch: python/conditional-based