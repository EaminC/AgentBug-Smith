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

RUN apt-get update && apt-get install -y --no-install-recommends \
    make \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY . .

# Set PYTHONPATH for multi-package layout
ENV PYTHONPATH=/app/libs/langgraph:/app:$PYTHONPATH

# Install dependencies and package in editable mode
RUN python -m pip install --upgrade pip wheel uv && \
    if [ -f libs/langgraph/uv.lock ]; then \
        cd libs/langgraph && \
        uv sync --frozen --group test --no-dev && \
        pip install -e . && \
        pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai; \
    elif [ -f libs/langgraph/pyproject.toml ]; then \
        cd libs/langgraph && \
        pip install -e . && \
        pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai; \
    else \
        echo "No recognized dependency file found in libs/langgraph" && exit 1; \
    fi

# Verify installation
RUN cd libs/langgraph && python -c "import langgraph; print(f'langgraph version: {langgraph.__version__}')"

# Default command to run tests
CMD ["pytest", "tests/agentsmith_fail2pass_6585.py", "-v"]