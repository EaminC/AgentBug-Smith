FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy entire repository to /app
COPY . .

# Upgrade pip, setuptools, wheel
RUN python -m pip install --upgrade pip setuptools wheel

# Install the local package in editable mode unconditionally
RUN pip install -e . && \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm

# Set Forge API environment variables for OpenAI and Anthropic SDK compatibility
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"

# Set PYTHONPATH for src/ layout
ENV PYTHONPATH=/app/src

# Unbuffered stdout
ENV PYTHONUNBUFFERED=1

# Default entrypoint is a bash shell
CMD ["/bin/bash"]