FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="openrouter2/openai/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="openrouter2/openai/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="openrouter2/openai/gpt-4.1-mini"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

# --- Inject environment variables for Forge API compatibility ---
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co \
    ANTHROPIC_AUTH_TOKEN=forge-key \
    FORGE_API_KEY="forge-key" \
    FORGE_BASE_URL=https://api.forge.tensorblock.co/v1

# Set working directory
WORKDIR /app

# Copy entire repository
COPY . .

# Upgrade pip, setuptools and wheel
RUN python -m pip install --upgrade pip setuptools wheel

# Install system dependencies required for compiling common Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libffi-dev libssl-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies:
#  - If requirements.txt exists, install it
#  - Then install the package itself in editable mode
#  - Then install required test packages except pytest-block-network which is unavailable
RUN if [ -f "requirements.txt" ]; then \
        pip install -r requirements.txt; \
    fi && \
    pip install -e . && \
    pip install --no-cache-dir pytest pytest-mock pytest-xdist pytest-timeout "setuptools<=81.0.0" litellm

# Set PYTHONPATH to support src/ layout if present, else default to /app
ENV PYTHONPATH=/app
RUN if [ -d "src" ]; then \
        export PYTHONPATH=/app:/app/src && echo "Set PYTHONPATH to /app:/app/src"; \
    else \
        echo "Using PYTHONPATH=/app"; \
    fi

# Default command to keep container open with bash for tests or interaction
CMD ["/bin/bash"]

# branch: python/requirements.txt
