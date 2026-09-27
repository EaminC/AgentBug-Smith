FROM python:3.12-slim

# Inject environment variables (from the original failing setup)
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

# Set working directory
WORKDIR /app

# Copy entire repository to container
COPY . .

# Install system dependencies, python packages including test dependencies and repo itself
RUN python -m pip install --upgrade pip setuptools wheel \
    && if [ -f requirements.txt ]; then pip install -r requirements.txt; fi \
    && pip install -e . \
    && pip install pytest pytest-mock pytest-asyncio pytest-cov anyio litellm pytest-xdist pytest-timeout mem0ai "setuptools<=81.0.0" \
    && rm -rf /var/lib/apt/lists/*

# Set PYTHONPATH to src directory for imports to work correctly
ENV PYTHONPATH=/app/src

# Verify the environment can import key packages
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

CMD ["/bin/bash"]