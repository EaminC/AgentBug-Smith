FROM python:3.12-slim AS test_builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

# Copy entire repo
COPY . .

# Install dependencies and project
RUN python -m pip install --upgrade pip wheel && \
    if [ -f requirements.txt ]; then \
        pip install -r requirements.txt; \
    fi && \
    pip install -e . && \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Ensure mle module can be imported
RUN python -c "import mle; print('mle import OK')"

# Set PYTHONPATH
ENV PYTHONPATH=/app

# Default command
CMD ["bash"]