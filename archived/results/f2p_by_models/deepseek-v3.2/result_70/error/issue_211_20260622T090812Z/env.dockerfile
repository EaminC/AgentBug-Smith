FROM python:3.12-slim

WORKDIR /app

# Copy all files first
COPY . .

# Install system dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install the project in editable mode unconditionally
RUN pip install --upgrade pip wheel setuptools && \
    pip install -e .

# Install dependencies from requirements.txt if it exists
RUN if [ -f requirements.txt ]; then \
        pip install -r requirements.txt; \
    fi

# Install test dependencies
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio litellm pytest-xdist pytest-timeout mem0ai

# Set PYTHONPATH to include /app for any src layout
ENV PYTHONPATH=/app:$PYTHONPATH

# Verify installation
RUN python -c "import pkg_resources; print('Installation verified')"

CMD ["/bin/bash"]