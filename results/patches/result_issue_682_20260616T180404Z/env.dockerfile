FROM python:3.12-slim

# --- Universal Build & Dynamic Versioning Overrides ---
ENV SETUPTOOLS_SCM_PRETEND_VERSION="0.0.1.dev0"
ENV POETRY_DYNAMIC_VERSIONING_BYPASS="0.0.1.dev0"
ENV HATCH_VCS_RECORD_FILE="/tmp/_version.py"
RUN git config --global --add safe.directory '*' || true
ENV SETUPTOOLS_SCM_PRETEND_VERSION_FOR_GPT_ENGINEER="0.0.1.dev0"
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

# Install system dependencies needed for tkinter
RUN apt-get update && apt-get install -y tk && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install build tools
RUN python -m pip install --upgrade pip setuptools wheel

# Copy the entire repository
COPY . .

# Install project dependencies with compatible versions
# Use langchain 0.0.x which has the get_openai_token_cost_for_model function
# Also need to ensure openai 0.27.8 is used (not 2.x from litellm dependencies)
RUN pip install "langchain==0.0.340" "openai==0.27.8" "pydantic<2.0.0" "pytest==7.3.1" "python-dotenv==0.21.1" && \
    pip install -e . && \
    pip install pytest-mock pytest-asyncio pytest-cov pytest-vcr anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout && \
    pip install --force-reinstall "openai==0.27.8"

# Verify critical imports work
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

CMD ["/bin/bash"]

# Install mini-swe-agent and set configuration flag
RUN pip install --no-cache-dir mini-swe-agent && \
    mkdir -p /root/.config/mini-swe-agent && \
    echo "MSWEA_CONFIGURED=true" > /root/.config/mini-swe-agent/.env
