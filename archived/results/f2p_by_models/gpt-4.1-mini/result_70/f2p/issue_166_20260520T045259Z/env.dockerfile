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

WORKDIR /app

COPY . .

ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co \
    ANTHROPIC_AUTH_TOKEN=forge-key

RUN set -eux; \
    python -m pip install --upgrade pip setuptools wheel;

RUN set -eux; \
    if [ -d "src" ] || grep -RqE "^\s*from src\.|^\s*import src\." tests 2>/dev/null; then \
        echo "src layout detected"; \
        SRC_LAYOUT=1; \
    else \
        SRC_LAYOUT=0; \
    fi; \
    echo $SRC_LAYOUT > .src_layout_flag

RUN set -eux; \
    if [ -f requirements.txt ]; then \
        if [ "$(cat .src_layout_flag)" = "1" ]; then \
            pip install -r requirements.txt; \
            pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout; \
            echo "export PYTHONPATH=/app" >> /root/.bashrc; \
        else \
            pip install -r requirements.txt; \
            pip install -e .; \
            pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout; \
        fi; \
    elif [ -f pyproject.toml ] && [ -f poetry.lock ]; then \
        pip install poetry; \
        poetry config virtualenvs.create false; \
        poetry install --no-interaction --no-ansi; \
        if [ "$(cat .src_layout_flag)" = "1" ]; then \
            pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout; \
            echo "export PYTHONPATH=/app" >> /root/.bashrc; \
        else \
            pip install -e .; \
            pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout; \
        fi; \
    elif [ -f pyproject.toml ]; then \
        if [ "$(cat .src_layout_flag)" = "1" ]; then \
            pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout; \
            echo "export PYTHONPATH=/app" >> /root/.bashrc; \
        else \
            pip install -e .; \
            pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout; \
        fi; \
    else \
        pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout; \
    fi

RUN set -eux; \
    if [ "$(cat .src_layout_flag)" = "1" ]; then \
        echo "export PYTHONPATH=/app" >> /root/.bashrc; \
    fi

RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

CMD ["/bin/bash"]
# branch: python/requirements.txt
