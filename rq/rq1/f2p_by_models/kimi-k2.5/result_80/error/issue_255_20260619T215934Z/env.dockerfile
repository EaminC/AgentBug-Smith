FROM python:3.9-slim

WORKDIR /app

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy source code
COPY . .

# Install dependencies safely with conditional checks
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi
RUN if [ -f requirements-dev.txt ]; then pip install --no-cache-dir -r requirements-dev.txt; fi

# Install the package in editable mode unconditionally
RUN pip install -e .

# Handle potential multi-package/monorepo layouts
# Check for common subpackage locations and install if they exist
RUN if [ -d src/agentscope ]; then pip install -e .; fi
RUN if [ -f setup.py ] || [ -f pyproject.toml ]; then pip install -e .; fi

# Explicitly configure PYTHONPATH for multi-package support
ENV PYTHONPATH=/app:/app/src:/app/libs:/app/packages

# Environment variables for API access (using injected values)
ENV FORGE_API_KEY="${FORGE_API_KEY}"
ENV FORGE_BASE_URL="${FORGE_BASE_URL}"
ENV MODEL="${MODEL}"
ENV DASHSCOPE_API_KEY="${FORGE_API_KEY}"
ENV OPENAI_API_KEY="${OPENAI_API_KEY}"

# Default to running pytest
CMD ["pytest", "-v"]