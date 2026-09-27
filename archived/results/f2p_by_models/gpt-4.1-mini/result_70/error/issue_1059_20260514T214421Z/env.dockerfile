FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tensorblock/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV GITHUB_TOKEN="ghp_key"
ENV TAVILY_API_KEY="tvly_key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tensorblock/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="tensorblock/gpt-4.1-mini"
ENV OPENAI_API_KEY="forge-key"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
# --- end inject ---

# Set environment variables for Forge API compatibility
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co \
    ANTHROPIC_AUTH_TOKEN=forge-key \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Set working directory
WORKDIR /app

# Copy entire repository
COPY . .

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc python3-dev libffi-dev libssl-dev libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and pin setuptools to 81.0.0 to fix compatibility issues
RUN python -m pip install --upgrade pip setuptools==81.0.0 wheel

# Install Python dependencies if requirements.txt exists
RUN if [ -f requirements.txt ]; then \
      sed -i 's/llama-index-vector-stores-faiss==0.1.1/llama-index-vector-stores-faiss>=0.1.2/g' requirements.txt && \
      sed -i 's/faiss_cpu==1.7.4/faiss_cpu/g' requirements.txt && \
      pip install --no-cache-dir numpy && \
      pip install --no-cache-dir -r requirements.txt; \
    else \
      echo "No requirements.txt found, skipping."; \
    fi

# Install repository itself in editable mode plus test dependencies
RUN pip install -e . pytest pytest-mock pytest-xdist pytest-timeout pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm

# Preflight: verify packages installed
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Entrypoint for test framework compatibility
CMD ["/bin/bash"]