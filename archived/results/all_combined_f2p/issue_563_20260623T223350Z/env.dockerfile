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

# Copy entire repository to ensure test scripts are present
COPY . .

# Upgrade pip and install wheel
RUN python -m pip install --upgrade pip wheel

# Install dependencies from pyproject.toml and the package itself
# According to pyproject.toml, dependencies are listed under [project]
# Use pip install -e . to install the package and its dependencies
RUN pip install -e .

# CRITICAL: Ensure pytest and other test dependencies are installed
# The pyproject.toml already includes pytest==7.3.1, but we also need extra test utilities
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Preflight import check to fail fast if core modules are missing
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# The final CMD is set to bash for interactive debugging (as required by test harness)
CMD ["/bin/bash"]