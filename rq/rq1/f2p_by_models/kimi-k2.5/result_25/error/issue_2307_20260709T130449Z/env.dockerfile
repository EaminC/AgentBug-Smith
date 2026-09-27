# CrewAI Dockerfile with Forge API configuration
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

# Set all environment variables in a single layer
ENV FORGE_API_KEY="forge-key" \
    FORGE_BASE_URL="https://api.forge.tensorblock.co/v1" \
    OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1" \
    OPENAI_API_KEY="forge-key" \
    ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1" \
    ANTHROPIC_AUTH_TOKEN="forge-key" \
    ANTHROPIC_MODEL="tuzi-kimi-k2.5/kimi-k2.5" \
    ANTHROPIC_SMALL_FAST_MODEL="tuzi-kimi-k2.5/kimi-k2.5" \
    MODEL="tuzi-kimi-k2.5/kimi-k2.5" \
    AI_TEMPERATURE="0.7" \
    TAVILY_API_KEY="tvly-dev-key" \
    GITHUB_TOKEN="ghp_key" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src

WORKDIR /app

# Copy the entire repository
COPY . .

# Install system dependencies, Python packages, and cleanup in one RUN
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        python3-dev \
        libxml2-dev \
        libxslt1-dev \
        git \
        && \
    pip install --no-cache-dir --upgrade pip wheel "setuptools<=81.0.0" && \
    pip install --no-cache-dir \
        pydantic>=2.4.2 \
        openai>=1.13.3 \
        litellm==1.60.2 \
        instructor>=1.3.3 \
        pdfplumber>=0.11.4 \
        regex>=2024.9.11 \
        opentelemetry-api>=1.30.0 \
        opentelemetry-sdk>=1.30.0 \
        opentelemetry-exporter-otlp-proto-http>=1.30.0 \
        chromadb>=0.5.23 \
        openpyxl>=3.1.5 \
        pyvis>=0.3.2 \
        auth0-python>=4.7.1 \
        python-dotenv>=1.0.0 \
        click>=8.1.7 \
        appdirs>=1.4.4 \
        jsonref>=1.1.0 \
        json-repair>=0.25.2 \
        uv>=0.4.25 \
        tomli-w>=1.1.0 \
        tomli>=2.0.2 \
        blinker>=1.9.0 \
        json5>=0.10.0 \
        pytest>=8.0.0 \
        pytest-mock \
        pytest-asyncio>=0.23.7 \
        pytest-vcr>=1.0.2 \
        pytest-subprocess>=1.5.2 \
        pytest-cov \
        mem0ai>=0.1.29 \
        crewai-tools~=0.40.1 \
        tiktoken~=0.7.0 \
        && \
    apt-get purge -y --auto-remove gcc g++ python3-dev && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /root/.cache/pip

# Pre-flight check
RUN python -c "import crewai, pytest; print('preflight ok')"

CMD ["/bin/bash"]
