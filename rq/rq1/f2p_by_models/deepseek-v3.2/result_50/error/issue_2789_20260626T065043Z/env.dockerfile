FROM python:3.12-slim AS test_builder

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

WORKDIR /app

# Install system dependencies needed for some Python packages (e.g., pdfplumber, chromadb)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy entire repository (required for external test script injection)
COPY . .

# Upgrade pip and wheel, install dependencies based on evidence from repository files.
# The project uses uv as the package manager (pyproject.toml [tool.uv] section, .github/workflows/tests.yml).
# Prefer uv sync if uv.lock exists; otherwise fallback to pip install.
# The project includes optional extras; install all extras for testing (as done in CI).
# CRITICAL: Install the local package in editable mode
RUN python -m pip install --upgrade pip wheel && \
    if [ -f uv.lock ]; then \
        uv sync --dev --all-extras; \
    else \
        pip install -e .[tools,embeddings,agentops,fastembed,pdfplumber,pandas,openxyxl,mem0,docling,aisuite]; \
    fi && \
    # Mandatory test framework installation (including litellm and setuptools<=81.0.0)
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai && \
    # Preflight import check to ensure core modules are accessible
    python -c 'import pkg_resources, pytest; print("preflight ok")'

# Set PYTHONPATH to include the src directory so tests can import crewai directly
ENV PYTHONPATH=/app/src:$PYTHONPATH

# The test harness will run pytest; final CMD is bash for manual inspection if needed
CMD ["/bin/bash"]