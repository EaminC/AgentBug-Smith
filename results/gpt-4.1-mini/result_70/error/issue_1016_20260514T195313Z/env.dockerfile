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

# Set working directory
WORKDIR /app

# Set environment variables to use Forge API instead of OpenAI API
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1 \
    ANTHROPIC_AUTH_TOKEN=forge-key \
    FORGE_API_KEY=forge-key \
    FORGE_BASE_URL=https://api.forge.tensorblock.co/v1

# Explicitly set PYTHONPATH to include main app and libs if present
ENV PYTHONPATH=/app:/app/libs:/app/packages

# Copy all repository files
COPY . .

# Upgrade pip, setuptools, wheel early
RUN python -m pip install --upgrade pip setuptools wheel

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libffi-dev libssl-dev python3-dev pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install requirements excluding faiss_cpu if requirements.txt exists
RUN if [ -f requirements.txt ]; then \
    grep -v '^faiss_cpu' requirements.txt > requirements_no_faiss.txt; \
    pip install -r requirements_no_faiss.txt; \
    fi

# Install a compatible faiss-cpu version manually
RUN pip install faiss-cpu==1.13.2

# Install all sub-packages in editable mode if multi-package layout detected
# Adjust these paths if your repo structure differs
RUN pip install -e . -e libs/langgraph -e libs/prebuilt -e libs/sdk-py || pip install -e .

# Install test dependencies
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio pytest-xdist pytest-timeout "setuptools<=81.0.0" litellm

# Preflight validation to confirm core dependencies
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Default command to run bash shell
CMD ["/bin/bash"]