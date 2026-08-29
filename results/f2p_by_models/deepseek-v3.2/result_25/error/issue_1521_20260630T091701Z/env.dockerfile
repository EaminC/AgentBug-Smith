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

# Copy entire repository (mandatory for test harness injection)
COPY . .

# Update pip and install wheel with proper quoting
RUN python -m pip install --upgrade "pip" "wheel" "setuptools<=81.0.0"

# Install uv for dependency management
RUN pip install uv

# Install project and dev dependencies using uv sync (as per CI)
RUN uv sync --dev

# Install additional test packages that might not be in dev dependencies
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio litellm pytest-xdist pytest-timeout mem0ai

# Install the local project in editable mode (CRITICAL)
RUN pip install -e .

# Preflight import check to ensure core modules can be imported
RUN python -c "import crewai, pytest, pydantic, langchain, openai; print('preflight ok')"

# Set PYTHONPATH to /app to avoid duplicate module loading
ENV PYTHONPATH=/app

CMD ["/bin/bash"]