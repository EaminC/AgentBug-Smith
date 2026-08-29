FROM python:3.12-slim

# --- Universal Build & Dynamic Versioning Overrides ---
ENV SETUPTOOLS_SCM_PRETEND_VERSION="0.0.1.dev0"
ENV POETRY_DYNAMIC_VERSIONING_BYPASS="0.0.1.dev0"
ENV HATCH_VCS_RECORD_FILE="/tmp/_version.py"
RUN git config --global --add safe.directory '*' || true
ENV SETUPTOOLS_SCM_PRETEND_VERSION_FOR_MLE_AGENT="0.0.1.dev0"
# -----------------------------------------------------


# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="openai/tuzi-deepseek-v3.2/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV GITHUB_TOKEN="ghp_key"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV ANTHROPIC_BASE_URL="anthropic_base_url"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tensorblock/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="tensorblock/gpt-4.1-mini"
ENV OPENAI_API_KEY="forge-key"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
# --- end inject ---

WORKDIR /app

COPY . .

RUN python -m pip install --upgrade pip setuptools wheel

RUN set -e; \
    if [ -d "src" ] || grep -Rq '^\s*from src\.|^\s*import src\.' . 2>/dev/null; then \
        echo "src layout detected"; \
        export PYTHONPATH=/app; \
        pip install -r requirements.txt 2>/dev/null || true; \
        pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout prettytable colorama; \
        echo "export PYTHONPATH=/app" >> /root/.bashrc; \
    else \
        pip install -r requirements.txt && pip install -e . && \
        pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout prettytable colorama; \
    fi

RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

CMD ["/bin/bash"]

# branch: python/requirements.txt

# Install mini-swe-agent and set configuration flag
RUN pip install --no-cache-dir mini-swe-agent && \
    mkdir -p /root/.config/mini-swe-agent && \
    echo "MSWEA_CONFIGURED=true" > /root/.config/mini-swe-agent/.env
