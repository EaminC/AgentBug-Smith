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
    ANTHROPIC_AUTH_TOKEN=forge-key

WORKDIR /app

# Copy all project files
COPY . .

# Install system dependencies needed to build Python packages and test dependencies
RUN set -ex \
    && apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        libpq-dev \
        libssl-dev \
        libffi-dev \
        libxml2-dev \
        libxslt1-dev \
        pkg-config \
        curl \
        python3-distutils-extra \
        build-essential \
        python3-venv \
    # Upgrade pip, wheel, and setuptools (pin setuptools to 81.0.0 for Python 3.12 compatibility)
    && python -m pip install --upgrade pip wheel setuptools==81.0.0 setuptools_scm packaging \
    # Patch faiss_cpu if present in requirements.txt
    && if [ -f requirements.txt ]; then sed -i 's/faiss_cpu==1.7.4/faiss_cpu==1.13.2/g' requirements.txt; fi \
    # Install dependencies from requirements.txt if present
    && if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; else echo "No requirements.txt found, skipping"; fi \
    # Install the project itself in editable mode unconditionally
    && pip install --no-cache-dir -e . \
    # Install test dependencies unconditionally
    && pip install --no-cache-dir pytest pytest-mock pytest-asyncio pytest-cov anyio pytest-xdist pytest-timeout litellm \
    # Cleanup build dependencies
    && apt-get remove -y build-essential gcc g++ \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /root/.cache/pip

# Set PYTHONPATH to include /app for local imports
ENV PYTHONPATH=/app

# Verify installs are successful
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Use bash as entrypoint
CMD ["/bin/bash"]