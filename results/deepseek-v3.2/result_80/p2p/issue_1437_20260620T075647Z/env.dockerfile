FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends git curl && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN python -m pip install --upgrade pip setuptools wheel

# Copy entire repository
COPY . .

# Install project in editable mode unconditionally
RUN pip install -e .

# Install test dependencies
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Set PYTHONPATH to include /app for imports
ENV PYTHONPATH=/app:$PYTHONPATH

# Set environment variables for testing (mock values)
ENV OPENAI_API_KEY=mock-key
ENV ANTHROPIC_AUTH_TOKEN=mock-token
ENV TAVILY_API_KEY=mock-key

# Verify installation
RUN python -c "import pytest; print('Installation verified')"

CMD ["/bin/bash"]