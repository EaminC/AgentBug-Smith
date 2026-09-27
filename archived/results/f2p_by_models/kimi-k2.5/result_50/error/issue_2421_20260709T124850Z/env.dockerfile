# Optimized Dockerfile for CrewAI with Forge API - Minimized for disk space
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

# Combine all ENV into single layer
ENV FORGE_API_KEY="forge-key" \
    FORGE_BASE_URL="https://api.forge.tensorblock.co/v1" \
    MODEL="tuzi-kimi-k2.5/kimi-k2.5" \
    AI_TEMPERATURE="0.7" \
    ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1" \
    ANTHROPIC_AUTH_TOKEN="forge-key" \
    ANTHROPIC_MODEL="tuzi-kimi-k2.5/kimi-k2.5" \
    ANTHROPIC_SMALL_FAST_MODEL="tuzi-kimi-k2.5/kimi-k2.5" \
    OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1" \
    OPENAI_API_KEY="forge-key" \
    TAVILY_API_KEY="tvly-dev-key" \
    GITHUB_TOKEN="ghp_key" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src

# Single RUN layer: install deps, cleanup
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc python3-dev && \
    pip install --no-cache-dir --upgrade pip wheel "setuptools<=81.0.0" && \
    pip install --no-cache-dir \
        pydantic>=2.4.2 \
        openai>=1.13.3 \
        litellm==1.74.3 \
        instructor>=1.3.3 \
        pytest>=8.0.0 \
        pytest-asyncio>=0.23.7 \
        pytest-mock \
        pytest-timeout \
        pytest-xdist \
        mem0ai>=0.1.94 \
        chromadb>=0.5.23 \
        blinker>=1.9.0 \
        pdfplumber>=0.11.4 \
        python-dotenv>=1.0.0 \
        click>=8.1.7 \
        appdirs>=1.4.4 \
        jsonref>=1.1.0 \
        json-repair==0.25.2 \
        tomli>=2.0.2 \
        tomli-w>=1.1.0 \
        tokenizers>=0.20.3 \
        pyjwt>=2.9.0 \
        openpyxl>=3.1.5 \
        regex>=2024.9.11 \
        pyvis>=0.3.2 \
        opentelemetry-api>=1.30.0 \
        opentelemetry-sdk>=1.30.0 \
        opentelemetry-exporter-otlp-proto-http>=1.30.0 && \
    apt-get purge -y --auto-remove gcc python3-dev && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /root/.cache

# Copy repository after dependency installation
COPY . .

# Install the project itself (if pyproject.toml exists)
RUN if [ -f "pyproject.toml" ] || [ -f "setup.py" ]; then \
        pip install --no-cache-dir -e . || true; \
    fi

CMD ["/bin/bash"]
