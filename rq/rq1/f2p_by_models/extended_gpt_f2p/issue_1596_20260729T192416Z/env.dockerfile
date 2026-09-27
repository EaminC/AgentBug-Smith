FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tuzi-gpt-4.1-mini/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tuzi-gpt-4.1-mini/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi-gpt-4.1-mini/gpt-4.1-mini"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

WORKDIR /app

COPY . .

ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1
ENV ANTHROPIC_AUTH_TOKEN=forge-key

RUN if [ -f "requirements.txt" ]; then \
        python -m pip install --upgrade pip setuptools wheel && \
        pip install -r requirements.txt && \
        pip install -e . && \
        pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai fakeredis apscheduler fastapi aiofiles; \
    elif [ -f "pyproject.toml" ] && [ -f "poetry.lock" ]; then \
        python -m pip install --upgrade pip setuptools wheel && \
        pip install poetry && \
        poetry config virtualenvs.create false && \
        poetry install --no-interaction --no-ansi && \
        pip install -e . && \
        pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai fakeredis apscheduler fastapi aiofiles; \
    elif [ -f "pyproject.toml" ]; then \
        python -m pip install --upgrade pip setuptools wheel && \
        pip install -e . && \
        pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai fakeredis apscheduler fastapi aiofiles; \
    else \
        python -m pip install --upgrade pip setuptools wheel && \
        pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai fakeredis apscheduler fastapi aiofiles; \
    fi

RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

CMD ["/bin/bash"]