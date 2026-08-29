FROM python:3.11-slim AS test_builder

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tuzi/deepseek-v3.2"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tuzi/deepseek-v3.2"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi/deepseek-v3.2"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ git curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade packaging tools
RUN python -m pip install --upgrade pip setuptools wheel

# Copy entire repository
COPY . .

# Install huggingface_hub with a compatible version that has ModelFilter
# ModelFilter was introduced in huggingface_hub>=0.17.0
RUN python -m pip install --upgrade pip setuptools wheel && \
    pip install "huggingface_hub>=0.17.0"

# Install project dependencies
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

# Install the project in editable mode
RUN pip install -e .

# Install test dependencies
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio litellm

# Set PYTHONPATH to include the project root
ENV PYTHONPATH=/app

# Preflight import check
RUN python -c "import sys; print(f'Python path: {sys.path}')" && \
    python -c "import agent; print('Agent module imported successfully')"

# Run the test file directly instead of unittest discovery
CMD ["python", "test_search_agent.py"]

FROM python:3.11-slim AS runtime

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Upgrade packaging tools
RUN python -m pip install --upgrade pip setuptools wheel

# Copy from test_builder
COPY --from=test_builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=test_builder /usr/local/bin /usr/local/bin
COPY . .

# Install production dependencies
RUN python -m pip install --upgrade pip setuptools wheel && \
    if [ -f requirements.txt ]; then pip install -r requirements.txt; fi && \
    pip install -e . --no-deps

# Set required environment variables
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co
ENV ANTHROPIC_AUTH_TOKEN=forge-key

ENTRYPOINT ["mle"]
CMD ["/bin/bash"]