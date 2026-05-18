FROM python:3.11-slim

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

# Set environment variables for Forge API (OpenAI-compatible and Anthropic-compatible)
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"

# Set working directory inside container
WORKDIR /app

# Copy the entire repository into the container
COPY . .

# Install system dependencies needed for Python packages (including compilation tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libxml2-dev libxslt1-dev python3-dev \
  && rm -rf /var/lib/apt/lists/*

# Upgrade pip, setuptools, wheel
RUN python3 -m pip install --upgrade pip setuptools wheel

# Install Python dependencies and the package itself using python 3.11
RUN if [ -f requirements.txt ]; then \
      pip install -r requirements.txt; \
    fi && \
    pip install -e . && \
    pip install pytest pytest-mock pytest-xdist pytest-timeout "setuptools<=81.0.0" litellm

# Set PYTHONPATH to include the app directory for imports
ENV PYTHONPATH=/app

# Verify critical packages are installed correctly
RUN python3 -c 'import pkg_resources, pytest; print("preflight ok")'

# The final CMD as required for testing harness
CMD ["/bin/bash"]

# branch: python with python:3.11-slim base, Forge API env vars, robust install including test deps, PYTHONPATH set