# CrewAI Python Project Dockerfile - Optimized for minimal disk usage
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

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src

WORKDIR /app

# Install system dependencies and Python packages in a single layer to minimize disk usage
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libxml2-dev \
    libxslt1-dev \
    python3-dev \
    && pip install --no-cache-dir --upgrade pip wheel "setuptools<=81.0.0" \
    && pip install --no-cache-dir \
    pydantic>=2.4.2 \
    "openai>=1.13.3" \
    litellm==1.74.9 \
    instructor>=1.3.3 \
    pdfplumber>=0.11.4 \
    regex>=2024.9.11 \
    openpyxl>=3.1.5 \
    pyvis>=0.3.2 \
    pandas>=2.2.3 \
    opentelemetry-api>=1.30.0 \
    opentelemetry-sdk>=1.30.0 \
    opentelemetry-exporter-otlp-proto-http>=1.30.0 \
    python-dotenv>=1.0.0 \
    pyjwt>=2.9.0 \
    click>=8.1.7 \
    appdirs>=1.4.4 \
    jsonref>=1.1.0 \
    "json-repair==0.25.2" \
    uv>=0.4.25 \
    tomli-w>=1.1.0 \
    tomli>=2.0.2 \
    blinker>=1.9.0 \
    json5>=0.10.0 \
    "portalocker==2.7.0" \
    chromadb>=0.5.23 \
    tokenizers>=0.20.3 \
    "onnxruntime==1.22.0" \
    tiktoken~=0.8.0 \
    pillow>=10.2.0 \
    cairosvg>=2.7.1 \
    mem0ai>=0.1.94 \
    docling>=2.12.0 \
    pytest>=8.0.0 \
    pytest-asyncio>=0.23.7 \
    pytest-mock \
    pytest-timeout>=2.3.1 \
    pytest-xdist>=3.6.1 \
    pytest-split>=0.9.0 \
    pytest-recording>=0.13.2 \
    pytest-randomly>=3.16.0 \
    pytest-subprocess>=1.5.2 \
    pyyaml \
    requests \
    && apt-get purge -y --auto-remove gcc g++ python3-dev libxml2-dev libxslt1-dev \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /root/.cache

# Copy the entire repository
COPY . /app/

# Install crewai package itself in editable mode
# Use --no-deps since we already installed all dependencies manually
RUN pip install --no-cache-dir --no-deps -e .

# Verify installation
RUN python -c "import crewai; import pytest; print('preflight ok')"

CMD ["/bin/bash"]
