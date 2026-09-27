FROM python:3.11-slim

WORKDIR /app

# Copy project files
COPY . /app/

# Set environment variables from the original
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

# Install system dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies safely
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
RUN if [ -f pyproject.toml ]; then pip install -e .; else pip install -e .; fi

# Set PYTHONPATH for multi-package layouts
ENV PYTHONPATH=/app:$PYTHONPATH

# Install pytest for running tests
RUN pip install pytest pytest-asyncio

# Default command
CMD ["python", "-m", "pytest", "tests/", "-v"]