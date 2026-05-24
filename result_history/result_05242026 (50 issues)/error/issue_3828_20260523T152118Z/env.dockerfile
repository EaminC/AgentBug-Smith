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

# Set environment variables for Forge API compatibility
ARG FORGE_API_KEY=forge-key
ENV FORGE_API_KEY=forge-key
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN=forge-key

# Set working directory
WORKDIR /app

# Install system dependencies needed for building Python packages and runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libffi-dev libssl-dev libxml2-dev libxslt1-dev python3-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Copy entire repository into the container
COPY . .

# Upgrade pip, setuptools, wheel
RUN python -m pip install --upgrade pip setuptools wheel

# Install dependencies and repository (editable) + test dependencies
RUN if [ -f "requirements.txt" ]; then \
      pip install -r requirements.txt; \
    fi && \
    pip install -e . && \
    pip install pytest pytest-mock pytest-xdist pytest-timeout "setuptools<=81.0.0" litellm mem0ai pyjwt chromadb json_repair appdirs cryptography opentelemetry-exporter-otlp-proto-http botocore

# Preflight to validate installs
RUN python -c 'import pkg_resources, pytest, cryptography, opentelemetry.exporter.otlp.proto.http, botocore; print("preflight ok")'

# Set PYTHONPATH explicitly if repository has sub-packages (adjust paths if needed)
ENV PYTHONPATH=/app

# Default command to open bash
CMD ["/bin/bash"]