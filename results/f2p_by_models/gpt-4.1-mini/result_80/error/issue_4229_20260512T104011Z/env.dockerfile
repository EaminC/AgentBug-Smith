# syntax=docker/dockerfile:1

FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tensorblock/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV GITHUB_TOKEN="ghp_key"
ENV TAVILY_API_KEY="tvly-key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tensorblock/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="tensorblock/gpt-4.1-mini"
ENV OPENAI_API_KEY="forge-key"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
# --- end inject ---

# Set environment variables for Forge API compatibility
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1 \
    ANTHROPIC_AUTH_TOKEN=forge-key

WORKDIR /app

# Install system dependencies and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc python3-dev libxml2-dev libxslt1-dev curl \
    && python3 -m pip install --upgrade pip setuptools wheel \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire repository into the container
COPY . .

# If multi-package layout detected, install all sub-packages in editable mode
# Detect sub-packages by presence of setup.py or pyproject.toml in subdirs libs/ or packages/
# For safety, install main project and libs if exist

RUN pip install --no-cache-dir pyyaml && \
    if [ -f requirements.txt ]; then \
        sed -i '/Items below this point will not be included in the Docker Image/,$d' requirements.txt || true; \
        sed -i '/playsound==1.2.2/d' requirements.txt || true; \
        pip install --no-cache-dir -r requirements.txt; \
    fi && \
    pip install --no-cache-dir -e . && \
    if [ -d libs/langgraph ]; then pip install --no-cache-dir -e libs/langgraph; fi && \
    if [ -d libs/prebuilt ]; then pip install --no-cache-dir -e libs/prebuilt; fi && \
    if [ -d libs/sdk-py ]; then pip install --no-cache-dir -e libs/sdk-py; fi && \
    pip install --no-cache-dir playsound==1.3.0 pytest pytest-mock pytest-asyncio pytest-cov anyio litellm pytest-xdist pytest-timeout 'setuptools<=81.0.0'

# Set PYTHONPATH explicitly for multi-package repo
ENV PYTHONPATH=/app/libs/langgraph:/app/libs/prebuilt:/app/libs/sdk-py:/app

# Preflight check to ensure pip packages import correctly
RUN python3 -c 'import pkg_resources, pytest; print("preflight ok")'

CMD ["/bin/bash"]