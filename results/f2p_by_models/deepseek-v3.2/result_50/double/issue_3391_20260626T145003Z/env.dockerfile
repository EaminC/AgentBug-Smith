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

# Copy entire repository
COPY . .

# Install system dependencies (if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install pip and upgrade
RUN python -m pip install --upgrade pip wheel

# First, install crewai since the test imports from it
RUN pip install crewai

# Check for uv.lock and pyproject.toml
RUN if [ -f uv.lock ] && [ -f pyproject.toml ]; then \
        pip install uv && \
        uv sync --all-groups --all-extras; \
    elif [ -f pyproject.toml ]; then \
        pip install -e .; \
    else \
        echo "No pyproject.toml found." && exit 1; \
    fi

# Install mandatory testing dependencies regardless of package manager
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Set PYTHONPATH to include the current directory for local imports
ENV PYTHONPATH=/app:$PYTHONPATH

# Preflight import check
RUN python -c 'import pkg_resources, pytest; import crewai; print("preflight ok")'

CMD ["/bin/bash"]