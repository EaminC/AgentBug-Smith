FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tensorblock/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV GITHUB_TOKEN="ghp_key"
ENV TAVILY_API_KEY="tvly-key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tensorblock/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="tensorblock/gpt-4.1-mini"
ENV OPENAI_API_KEY="forge-key"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
# --- end inject ---

# Set working directory
WORKDIR /app

# Set environment variables for Forge API compatibility with OpenAI and Anthropic SDKs
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1 \
    ANTHROPIC_AUTH_TOKEN=forge-key

# Install system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libc6-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and packaging tools
RUN python -m pip install --upgrade pip setuptools wheel

# Copy all files to the container
COPY . .

# Install python dependencies and the repo itself; then install test dependencies
RUN if [ -f "requirements.txt" ]; then \
    pip install -r requirements.txt; \
    fi && \
    pip install -e . && \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout huggingface_hub==0.16.4 numpy==1.24.4

# Install chromadb pinned to a version compatible with numpy 1.x to avoid np.float_ removal issues
RUN pip install "chromadb<0.4.0"

# Set PYTHONPATH to include /app and sub-packages if any (adjust if repo has sub-packages)
ENV PYTHONPATH=/app

# Preflight: ensure install and test framework work
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Default to bash shell
CMD ["/bin/bash"]