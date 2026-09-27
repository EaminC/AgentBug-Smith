FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_CACHE_DIR=/tmp/uv-cache

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv pytest

WORKDIR /workspaces/langchain
COPY . .

RUN mkdir -p $UV_CACHE_DIR && chmod 755 $UV_CACHE_DIR

# Install deps for core and v1 packages commonly referenced by selected tests.
RUN if [ -d "libs/core" ]; then cd libs/core && uv sync --dev --group test; fi
RUN if [ -d "libs/langchain_v1" ]; then cd libs/langchain_v1 && uv sync --dev --group test; fi
RUN if [ -d "libs/langchain" ]; then cd libs/langchain && uv sync --dev --group test; fi

WORKDIR /workspaces/langchain
CMD ["/bin/bash"]
