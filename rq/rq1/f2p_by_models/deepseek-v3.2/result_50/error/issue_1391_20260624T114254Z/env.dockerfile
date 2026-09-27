FROM python:3.12-slim

# Set environment variables (using placeholders for security)
ENV FORGE_API_KEY="test-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="test-key"
ENV ANTHROPIC_MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="test-key"
ENV TAVILY_API_KEY="test-key"
ENV GITHUB_TOKEN="test-key"

WORKDIR /app

# Copy entire repository
COPY . .

# Install system dependencies for possible build steps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies based on available files
RUN python -m pip install --upgrade pip wheel && \
    if [ -f "requirements.txt" ]; then \
        pip install -r requirements.txt; \
    fi && \
    if [ -f "pyproject.toml" ]; then \
        pip install -e .[test]; \
    elif [ -f "setup.py" ]; then \
        pip install -e .; \
    fi && \
    # Install test dependencies
    pip install pytest pytest-mock pytest-cov pytest-asyncio pytest-xdist pytest-timeout

# Set PYTHONPATH to include src directory
ENV PYTHONPATH=/app/src:$PYTHONPATH

# Verify installation
RUN python -c "import agentscope; print(f'Agentscope version: {agentscope.__version__}')"

CMD ["/bin/bash"]