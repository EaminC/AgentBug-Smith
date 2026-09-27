# CrewAI Dockerfile - Optimized build for src layout
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

WORKDIR /app

# Environment variables for Python and Forge API
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    FORGE_API_KEY="forge-key" \
    FORGE_BASE_URL="https://api.forge.tensorblock.co/v1" \
    MODEL="tuzi-kimi-k2.5/kimi-k2.5" \
    AI_TEMPERATURE="0.7" \
    AI_MAX_TOKENS="1000" \
    AI_TOP_P="1" \
    ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1" \
    ANTHROPIC_AUTH_TOKEN="forge-key" \
    ANTHROPIC_MODEL="tuzi-kimi-k2.5/kimi-k2.5" \
    ANTHROPIC_SMALL_FAST_MODEL="tuzi-kimi-k2.5/kimi-k2.5" \
    OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1" \
    OPENAI_API_KEY="forge-key" \
    TAVILY_API_KEY="tvly-dev-key" \
    GITHUB_TOKEN="ghp_key" \
    PYTHONPATH=/app/src

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git gcc g++ libxml2-dev libxslt1-dev libffi-dev libssl-dev python3-dev \
    && python -m pip install --upgrade pip wheel setuptools \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . .

# Install project dependencies safely and editable install
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi \
    && pip install --no-cache-dir -e .

# Install test dependencies
RUN pip install --no-cache-dir \
    pydantic>=2.4.2 \
    openai>=1.13.3 \
    litellm==1.72.0 \
    instructor>=1.3.3 \
    pdfplumber>=0.11.4 \
    chromadb>=0.5.23 \
    tokenizers>=0.20.3 \
    onnxruntime==1.22.0 \
    openpyxl>=3.1.5 \
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
    regex>=2024.9.11 \
    pyvis>=0.3.2 \
    opentelemetry-api>=1.30.0 \
    opentelemetry-sdk>=1.30.0 \
    opentelemetry-exporter-otlp-proto-http>=1.30.0 \
    pytest>=8.0.0 \
    pytest-asyncio>=0.23.7 \
    pytest-mock>=3.14.0 \
    pytest-timeout>=2.3.1 \
    pytest-subprocess>=1.5.2 \
    pytest-recording>=0.13.2 \
    pytest-randomly>=3.16.0 \
    anyio \
    mem0ai>=0.1.94 \
    "setuptools<=81.0.0" \
    && rm -rf /root/.cache/pip

# Verify installation
RUN python -c "import crewai; print('crewai imported successfully')" \
    && python -c "import pytest; print('pytest imported successfully')"

CMD ["/bin/bash"]