FROM python:3.12-slim AS test_builder

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
ENV ANTHROPIC_BASE_URL="anthropic_base_url"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

WORKDIR /app

# Copy entire repo to ensure test scripts are present
COPY . .

# Install system dependencies if any (none evident from files)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies, test framework, and the project itself
# Evidence: requirements.txt exists, setup.py uses requirements.txt
# No src/ layout detected (no src directory in repo root), so editable install is safe.
RUN python -m pip install --upgrade pip wheel && \
    pip install -r requirements.txt && \
    pip install -e . && \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Preflight import check to fail fast
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Run the project's unit tests as per .github/workflows/test.yml
CMD ["python", "-m", "unittest", "discover", "tests"]

# Install mini-swe-agent and set configuration flag
RUN pip install --no-cache-dir mini-swe-agent && \
    mkdir -p /root/.config/mini-swe-agent && \
    echo "MSWEA_CONFIGURED=true" > /root/.config/mini-swe-agent/.env
