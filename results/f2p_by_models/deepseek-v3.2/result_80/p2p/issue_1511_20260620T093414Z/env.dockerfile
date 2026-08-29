FROM python:3.12-slim AS test_builder

# Set environment variables
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1
ENV ANTHROPIC_AUTH_TOKEN=forge-key
ENV FORGE_API_KEY=forge-key
ENV FORGE_BASE_URL=https://api.forge.tensorblock.co/v1
ENV MODEL=tuzi-deepseek-v3.2/deepseek-v3.2
ENV AI_TEMPERATURE=0.7
ENV ANTHROPIC_MODEL=tuzi-deepseek-v3.2/deepseek-v3.2
ENV ANTHROPIC_SMALL_FAST_MODEL=tuzi-deepseek-v3.2/deepseek-v3.2
ENV TAVILY_API_KEY=tvly-dev-key
ENV GITHUB_TOKEN=ghp_key

# Set working directory
WORKDIR /app

# Copy entire repository
COPY . .

# Upgrade packaging tools
RUN python -m pip install --upgrade pip setuptools wheel

# Install project in editable mode (CRITICAL)
RUN pip install -e .

# Install requirements if file exists
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

# Install test dependencies
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Preflight import check
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Final command
CMD ["/bin/bash"]