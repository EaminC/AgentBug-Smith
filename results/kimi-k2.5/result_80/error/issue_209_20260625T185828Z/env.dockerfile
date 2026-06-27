FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project source
COPY . .

# Install requirements if present
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

# Install test dependencies if present
RUN if [ -f requirements-test.txt ]; then pip install -r requirements-test.txt; fi

# Editable install of the package (unconditional as per requirements)
RUN pip install -e .

# Set PYTHONPATH to include src if using src layout, otherwise app root
ENV PYTHONPATH=/app:/app/src:$PYTHONPATH

# Environment variables for API access (inherited from original config)
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

# Default command to run tests
CMD ["pytest", "tests/formatter_dashscope_test.py", "-v"]