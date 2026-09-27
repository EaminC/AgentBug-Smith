FROM python:3.9-slim

WORKDIR /app

# Install system dependencies if needed for building packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . .

# Install dependencies safely if requirements.txt exists
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

# Handle potential monorepo structure by checking for setup.py or pyproject.toml in subdirectories
# Install main package unconditionally in editable mode
RUN pip install -e .

# If this is a monorepo with libs/ structure, install sub-packages
RUN if [ -d libs ]; then \
    for dir in libs/*/; do \
        if [ -f "$dir/setup.py" ] || [ -f "$dir/pyproject.toml" ]; then \
            pip install -e "$dir" || true; \
        fi; \
    done; \
fi

# Set PYTHONPATH to include potential source directories for monorepo support
ENV PYTHONPATH=/app:/app/src:/app/libs:/app/packages

# Environment variables for API access (retained from original configuration)
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

# Default to running pytest
CMD ["python", "-m", "pytest", "tests/formatter_dashscope_test.py", "-v"]