FROM python:3.9-slim

WORKDIR /app

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy the repository code
COPY . .

# Set environment variables for API access and configuration
ENV PYTHONPATH=/app/src:/app
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

# Install Python dependencies safely (self-healing for missing files)
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

# Install the local package in editable mode (CRITICAL for import resolution)
RUN pip install -e .

# Install test framework
RUN pip install pytest pytest-asyncio

# Default command to run tests
CMD ["pytest", "tests/formatter_dashscope_test.py", "-v"]