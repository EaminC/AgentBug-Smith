FROM python:3.12-slim AS test_builder

# --- AgentSmith inject .env from project root (dockerwrite) ---
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
# --- end inject ---

WORKDIR /app

# Install system dependencies for Python packages that may need compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy entire repository (including externally-injected tests)
COPY . .

# Check for src layout or src imports to decide on editable install
WORKDIR /app

# First, check if we're in a Python project structure
RUN if [ -d "python" ]; then \
    echo "Python subdirectory found, switching to it"; \
    cd python; \
    fi

# Install the project in editable mode
RUN if [ -f "pyproject.toml" ] || [ -f "setup.py" ] || [ -f "setup.cfg" ]; then \
    pip install --upgrade pip setuptools wheel && \
    pip install -e .; \
    elif [ -f "requirements.txt" ]; then \
    pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt; \
    else \
    echo "No Python project structure found"; \
    fi

# Install test dependencies
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Set PYTHONPATH to include the current directory
ENV PYTHONPATH=/app:$PYTHONPATH

# Set Forge environment variables
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co
ENV ANTHROPIC_AUTH_TOKEN=forge-key

# Default command for test stage
CMD ["/bin/bash"]

# Production stage (minimal)
FROM python:3.12-slim

WORKDIR /app

# Install runtime system dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy only the Python project from test stage
COPY --from=test_builder /app /app
COPY --from=test_builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

# Set Forge environment variables in production
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co
ENV ANTHROPIC_AUTH_TOKEN=forge-key

# Expose port (inferred from README: web UI runs on port 1420)
EXPOSE 1420

CMD ["/bin/bash"]