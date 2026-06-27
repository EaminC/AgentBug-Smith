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

COPY . .

# Install dependencies based on project structure
RUN if [ -f requirements.txt ]; then \
        python -m pip install --upgrade pip wheel && \
        pip install -r requirements.txt; \
    elif [ -f pyproject.toml ] && [ -f poetry.lock ]; then \
        python -m pip install --upgrade pip wheel && \
        pip install poetry && \
        poetry config virtualenvs.create false && \
        poetry install --no-interaction --no-ansi; \
    elif [ -f pyproject.toml ]; then \
        python -m pip install --upgrade pip wheel; \
    else \
        echo "No recognized Python project files found, continuing with base setup"; \
    fi

# Install testing dependencies
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# CRITICAL: Unconditional editable install for local package
# Handle potential monorepo structures by installing common sub-packages
RUN if [ -f setup.py ] || [ -f pyproject.toml ]; then \
        pip install -e . || echo "Warning: editable install of root failed"; \
    fi

# Handle multi-package layouts (common in agent frameworks)
RUN for dir in src agentscope libs/agentscope; do \
        if [ -f "$dir/setup.py" ] || [ -f "$dir/pyproject.toml" ]; then \
            pip install -e "$dir" || echo "Warning: editable install of $dir failed"; \
        fi \
    done

# CRITICAL: Set PYTHONPATH for monorepo support
ENV PYTHONPATH=/app:/app/src:/app/libs:/app/agentscope:/app/packages

# Verify installation
RUN python -c 'import sys; print("Python path:", sys.path); import pytest; print("pytest ok")'

CMD ["/bin/bash"]