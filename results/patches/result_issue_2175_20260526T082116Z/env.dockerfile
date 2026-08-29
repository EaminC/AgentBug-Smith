FROM python:3.12-slim

# --- Universal Build & Dynamic Versioning Overrides ---
ENV SETUPTOOLS_SCM_PRETEND_VERSION="0.0.1.dev0"
ENV POETRY_DYNAMIC_VERSIONING_BYPASS="0.0.1.dev0"
ENV HATCH_VCS_RECORD_FILE="/tmp/_version.py"
RUN git config --global --add safe.directory '*' || true
ENV SETUPTOOLS_SCM_PRETEND_VERSION_FOR_CREWAI="0.0.1.dev0"
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

# Detect src layout or imports to set PYTHONPATH and install dependencies
RUN if [ -d "src" ] || grep -Rq '^[[:space:]]*from src\.|^[[:space:]]*import src\.' . ; then \
    echo "src layout detected, setting PYTHONPATH"; \
    echo "export PYTHONPATH=/app" > /etc/profile.d/pythonpath.sh; \
    export PYTHONPATH=/app; \
    if [ -f "requirements.txt" ]; then \
      pip install -r requirements.txt; \
    fi && \
    pip install -e . "pytest" "pytest-mock" "pytest-asyncio" "pytest-cov" "pytest-vcr" "anyio" "pytest-xdist" "pytest-timeout" "setuptools<=81.0.0" "litellm" "mem0ai" "embedchain" "langchain-community" "langchain<0.3.0"; \
else \
    if [ -f "requirements.txt" ]; then \
      pip install -r requirements.txt; \
    fi && \
    pip install -e . "pytest" "pytest-mock" "pytest-asyncio" "pytest-cov" "pytest-vcr" "anyio" "pytest-xdist" "pytest-timeout" "setuptools<=81.0.0" "litellm" "mem0ai" "embedchain" "langchain-community" "langchain<0.3.0"; \
fi

# Ensure PYTHONPATH is set explicitly for runtime
ENV PYTHONPATH=/app

RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

CMD ["/bin/bash"]

# Install mini-swe-agent and set configuration flag
RUN pip install --no-cache-dir mini-swe-agent && \
    mkdir -p /root/.config/mini-swe-agent && \
    echo "MSWEA_CONFIGURED=true" > /root/.config/mini-swe-agent/.env
