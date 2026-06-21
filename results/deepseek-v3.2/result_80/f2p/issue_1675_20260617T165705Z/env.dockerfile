FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

# Set additional Forge environment variables
ENV AI_MAX_TOKENS=1000
ENV AI_TOP_P=1
ENV AI_FREQUENCY_PENALTY=0
ENV AI_PRESENCE_PENALTY=0

WORKDIR /app

# Install system dependencies for Python packages and standalone script execution
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    libxml2-dev \
    libxslt1-dev \
    python3-dev \
    gcc \
    pkg-config \
    libffi-dev \
    libssl-dev \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire repository
COPY . .

# Upgrade packaging tools
RUN python -m pip install --upgrade pip setuptools wheel

# Create and activate virtual environment to avoid PEP 668 issues
RUN python -m venv /venv
ENV VIRTUAL_ENV=/venv
ENV PATH="/venv/bin:$PATH"

# Install dependencies and the project in virtual environment
# branch: python/requirements.txt
# Install all dependencies together to let pip resolve version conflicts
RUN if [ -f "requirements.txt" ]; then pip install -r requirements.txt; fi && \
    pip install pytest pytest-mock pytest-cov pytest-xdist pytest-timeout \
    "setuptools<=81.0.0" litellm mem0ai && \
    pip install -e .

# Install dev dependencies for comprehensive testing
RUN if [ -f "requirements/requirements-dev.txt" ]; then \
    pip install -r requirements/requirements-dev.txt; \
    fi

# Set PYTHONPATH for proper module resolution
ENV PYTHONPATH=/app

# Verify the project can be imported and basic functionality works
# Use proper Dockerfile syntax for multi-line Python command
RUN python -c "\
import sys; \
print(f'Python version: {sys.version}'); \
import aider; \
print(f'aider imported successfully from {aider.__file__}'); \
import aider.io; \
print('aider.io imported successfully'); \
io_instance = aider.io.InputOutput(); \
print('InputOutput instance created'); \
print(f'Has compute_minimal_fileids: {hasattr(io_instance, \"compute_minimal_fileids\")}'); \
print(f'Has format_files_for_input: {hasattr(io_instance, \"format_files_for_input\")}')"

# Verify pytest works and can discover tests
RUN python -c "import pytest; import sys; print('pytest imported successfully')"

# Verify standalone script execution capability with virtual environment
RUN echo '#!/usr/bin/env python\nimport sys\nprint("Standalone script test: OK")\nprint(f"Python {sys.version}")\nprint(f"Virtual env: {sys.prefix}")\nprint(f"Python path: {sys.path}")\n# Test basic imports\ntry:\n    import os\n    import json\n    import requests\n    print("Basic imports successful")\nexcept Exception as e:\n    print(f"Basic import error: {e}")' > /tmp/test_script.py && \
    python /tmp/test_script.py && \
    rm /tmp/test_script.py

# Preflight import check
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Default command (required by test harness)
CMD ["/bin/bash"]