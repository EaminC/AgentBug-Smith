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

ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co \
    ANTHROPIC_AUTH_TOKEN=forge-key \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libffi-dev libssl-dev libxml2-dev libxslt1-dev python3-dev libyaml-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --upgrade pip setuptools==81.0.0 wheel Cython

COPY . .

RUN if [ -f requirements.txt ]; then sed -i '/playsound==1.2.2/d' requirements.txt; fi

# Always install the local package in editable mode unconditionally
RUN pip install -e .

# Install dependencies conditionally and testing tools unconditionally
RUN if [ -f requirements.txt ]; then \
        PYYAML_FORCE_CYTHON=0 pip install -r requirements.txt; \
    elif [ -f pyproject.toml ] && [ -f poetry.lock ]; then \
        pip install poetry && poetry install; \
    fi

RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio litellm pytest-xdist pytest-timeout setuptools==81.0.0

RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

CMD ["/bin/bash"]