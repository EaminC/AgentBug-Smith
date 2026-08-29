FROM python:3.12-slim

# --- Universal Build & Dynamic Versioning Overrides ---
ENV SETUPTOOLS_SCM_PRETEND_VERSION="0.0.1.dev0"
ENV POETRY_DYNAMIC_VERSIONING_BYPASS="0.0.1.dev0"
ENV HATCH_VCS_RECORD_FILE="/tmp/_version.py"
RUN git config --global --add safe.directory '*' || true
# -----------------------------------------------------


# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tuzi-deepseek-v3.2/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV GITHUB_TOKEN="ghp_key"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV OPENAI_API_KEY="forge-key"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
# --- end inject ---

WORKDIR /app

# Copy entire repository
COPY . .

# Install system dependencies needed for Python packages and git
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
       gcc \
       python3-dev \
       libffi-dev \
       libssl-dev \
       git \
       && rm -rf /var/lib/apt/lists/*

# Upgrade pip, setuptools, wheel and install dependencies including tests and project
RUN python -m pip install --upgrade pip setuptools wheel; \
    if [ -f requirements.txt ]; then \
        pip install -r requirements.txt; \
    fi; \
    pip install -e .; \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio pytest-xdist pytest-timeout "setuptools<=81.0.0" litellm gitpython rich prompt_toolkit backoff pillow streamlit networkx pathspec playwright configargparse diskcache pypandoc grep-ast beautifulsoup4 tree-sitter-languages diff-match-patch

# Ensure python can import from /app root directory
ENV PYTHONPATH=/app

# Verify pytest and package install succeeded
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

CMD ["/bin/bash"]