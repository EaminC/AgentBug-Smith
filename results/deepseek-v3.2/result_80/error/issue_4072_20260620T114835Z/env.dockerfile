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
COPY . .

# Set Forge environment variables
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1
ENV ANTHROPIC_AUTH_TOKEN=forge-key

# Upgrade packaging tools
RUN python -m pip install --upgrade pip setuptools wheel

# Detect package structure and set PYTHONPATH
RUN if [ -d "src" ]; then \
    echo "src/ layout detected"; \
    export PYTHONPATH=/app/src:$PYTHONPATH; \
    elif [ -d "libs" ]; then \
    echo "libs/ layout detected"; \
    export PYTHONPATH=/app/libs:$PYTHONPATH; \
    elif [ -d "packages" ]; then \
    echo "packages/ layout detected"; \
    export PYTHONPATH=/app/packages:$PYTHONPATH; \
    else \
    echo "Flat layout detected"; \
    export PYTHONPATH=/app:$PYTHONPATH; \
    fi && \
    echo "PYTHONPATH set to: $PYTHONPATH"

# Install dependencies based on evidence from repository files
RUN if [ -f "uv.lock" ] && [ -f "pyproject.toml" ]; then \
    pip install uv && \
    uv pip install --system -r uv.lock; \
    elif [ -f "requirements.txt" ]; then \
    pip install -r requirements.txt; \
    elif [ -f "pyproject.toml" ]; then \
    pip install .; \
    else \
    echo "No dependency file found"; \
    fi

# CRITICAL: Unconditionally install project in editable mode
RUN if [ -f "setup.py" ] || [ -f "pyproject.toml" ]; then \
    pip install -e .; \
    else \
    echo "No setup.py or pyproject.toml found for editable install"; \
    fi

# Install mandatory testing dependencies (unconditionally)
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai vcrpy pytest-recording pytest-randomly pytest-subprocess

# Final PYTHONPATH setup
ENV PYTHONPATH=/app:$PYTHONPATH

# Preflight import check
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

CMD ["/bin/bash"]