# CrewAI Dockerfile - Space-optimized build with Forge API configuration
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

# Python optimizations
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PYTHONPATH="/app:/app/src"

WORKDIR /app

# Install system dependencies, Python packages, and project in a single layer with aggressive cleanup
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    git \
    libxml2-dev \
    libxslt1-dev \
    python3-dev \
    && pip install --no-cache-dir --upgrade pip wheel "setuptools<=81.0.0" \
    && pip install --no-cache-dir pytest pytest-asyncio pytest-mock pytest-xdist pytest-timeout pytest-recording pytest-randomly pytest-subprocess pytest-cov litellm mem0ai requests \
    && apt-get purge -y --auto-remove gcc g++ git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/* /tmp/* /var/tmp/* ~/.cache/pip /usr/share/doc /usr/share/man

# Copy project files
COPY . .

# Install requirements if they exist, then install crewai framework and project
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi \
    && pip install --no-cache-dir "crewai-tools~=0.47.1" \
    && pip install --no-cache-dir -e "." \
    && rm -rf ~/.cache/pip /tmp/pip-* /root/.cache /usr/local/lib/python3.12/site-packages/pip/_vendor/*/test* 2>/dev/null || true

# Handle monorepo layouts: install additional sub-packages if they exist
RUN if [ -f src/crewai/pyproject.toml ] || [ -f src/crewai/setup.py ]; then \
        pip install --no-cache-dir -e "src/crewai" || true; \
    fi \
    && if [ -d libs ] && [ -f libs/core/pyproject.toml ]; then \
        for dir in libs/*/; do \
            if [ -f "${dir}pyproject.toml" ] || [ -f "${dir}setup.py" ]; then \
                pip install --no-cache-dir -e "${dir}" || true; \
            fi \
        done \
    fi

# Verify editable installation and imports
RUN python -c "import crewai; import pytest; print('preflight ok')" || \
    PYTHONPATH="/app/src:$PYTHONPATH" python -c "import crewai; import pytest; print('preflight ok with src')"

CMD ["/bin/bash"]