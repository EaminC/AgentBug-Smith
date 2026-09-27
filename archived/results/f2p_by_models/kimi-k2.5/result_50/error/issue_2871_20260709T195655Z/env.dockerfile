# Dockerfile for AgentScope - Optimized for minimal disk usage
FROM python:3.11-slim

WORKDIR /app

# Set environment variables for Python and project
ENV PYTHONUNBUFFERED="1" \
    PYTHONDONTWRITEBYTECODE="1" \
    PYTHONPATH="/app/src:/app" \
    PIP_NO_CACHE_DIR="1" \
    PIP_DISABLE_PIP_VERSION_CHECK="1"

# Single RUN command to minimize layers: install system deps and cleanup
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        git \
        libffi-dev \
        libssl-dev \
        python3-dev && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/* /tmp/* /var/tmp/*

# Copy requirements first for better caching (safe file check)
COPY requirements*.txt ./
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

# Install test dependencies
RUN pip install --no-cache-dir pytest pytest-mock pytest-asyncio anyio

# Copy application code
COPY . .

# Install project in editable mode unconditionally
RUN pip install --no-cache-dir -e .

# Final cleanup to minimize image size
RUN rm -rf /root/.cache /var/cache/pip/* /tmp/* /var/tmp/* && \
    find /usr/local/lib/python3.11/site-packages -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true && \
    find /usr/local/lib/python3.11/site-packages -type f -name "*.pyc" -delete 2>/dev/null || true

# Verify installation of critical modules
RUN python -c "from agentscope.formatter import DashScopeChatFormatter; print('Import verification successful')"

CMD ["/bin/bash"]