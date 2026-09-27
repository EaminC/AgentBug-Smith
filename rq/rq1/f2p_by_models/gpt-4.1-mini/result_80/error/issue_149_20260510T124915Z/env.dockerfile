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

# Set environment variables for Forge API compatibility
ENV FORGE_API_KEY="forge-key" \
    OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1" \
    OPENAI_API_KEY="forge-key" \
    ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1" \
    ANTHROPIC_AUTH_TOKEN="forge-key"

# Set working directory to the repository root
WORKDIR /app

# Install system dependencies for building Python packages and general usage
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libssl-dev \
    curl \
    git \
  && rm -rf /var/lib/apt/lists/*

# Copy the entire repository into /app
COPY . .

# Upgrade pip, setuptools and wheel
RUN python -m pip install --upgrade pip setuptools wheel

# Install Dapr SDKs as the repo relates to dapr agents
RUN pip install "dapr>=1.13.0" "dapr-ext-grpc>=1.13.0"

# Install dependencies and project, and testing tools
RUN if [ -f "requirements.txt" ]; then \
    pip install -r requirements.txt; \
  fi && \
  pip install -e . && \
  pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm

# Check that import and testing environment works
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Default to bash for container
CMD ["/bin/bash"]