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

# Set environment variables for Forge API compatibility (OpenAI and Anthropic)
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1 \
    ANTHROPIC_AUTH_TOKEN=forge-key

# Set working directory to /app (repository root)
WORKDIR /app

# Copy the entire repository into the container
COPY . .

# Install system dependencies needed for building common Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev libssl-dev python3-dev \
 && rm -rf /var/lib/apt/lists/*

# Upgrade pip, setuptools, wheel
RUN python -m pip install --upgrade pip setuptools wheel

# Install project dependencies and testing packages
RUN if [ -f requirements.txt ]; then \
      pip install -r requirements.txt; \
    fi

# Always install the local project in editable mode
RUN pip install -e .

# Install testing and auxiliary packages unconditionally
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio pytest-xdist pytest-timeout litellm mem0ai "setuptools<=81.0.0"

# If the repo has sub-packages, install them in editable mode and set PYTHONPATH accordingly
# (Example: adjust these lines if your repo has such structure)
# RUN pip install -e libs/langgraph[tests] -e libs/prebuilt -e libs/sdk-py
# ENV PYTHONPATH=/app/libs/langgraph:/app/libs/prebuilt:/app/libs/sdk-py

# Verify that pytest and pkg_resources can be imported
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Default command: open a bash shell
CMD ["/bin/bash"]

# branch: python with conditional install and Forge API env