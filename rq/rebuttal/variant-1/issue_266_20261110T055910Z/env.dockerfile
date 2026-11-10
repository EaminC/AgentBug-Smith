FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="openrouter3/openai/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="openrouter3/openai/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="openrouter3/openai/gpt-4.1-mini"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

# Set environment variables for Forge API compatibility
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co \
    ANTHROPIC_AUTH_TOKEN=forge-key \
    FORGE_API_KEY=forge-key \
    FORGE_BASE_URL=https://api.forge.tensorblock.co/v1

# Working directory
WORKDIR /app

# Copy the full repository
COPY . .

# Install system dependencies needed for building some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libc6-dev libffi-dev && rm -rf /var/lib/apt/lists/*

# Upgrade pip, setuptools, wheel
RUN python -m pip install --upgrade pip setuptools wheel

# Install Python dependencies from requirements.txt if exists
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

# Install numpy >=2.0 for pyarrow compatibility
RUN pip install "numpy>=2.0"

# Install the local package in editable mode unconditionally
RUN pip install -e .

# Install testing dependencies (excluding pytest-block-network which is unavailable)
RUN pip install pytest pytest-mock pytest-xdist pytest-timeout "setuptools<=81.0.0" litellm "numpy<2.0" "pyarrow<16.0.0"

# Set PYTHONPATH for correct imports (adjust if repo has sub-packages)
ENV PYTHONPATH=/app

# Sanity check to verify packages
RUN python -c "import pkg_resources, pytest; print('preflight ok')"

CMD ["/bin/bash"]