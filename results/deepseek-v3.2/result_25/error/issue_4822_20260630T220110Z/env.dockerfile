FROM python:3.12-slim AS test_builder

# Set environment variables (use placeholders that can be overridden)
ENV FORGE_API_KEY=${FORGE_API_KEY:-test_key}
ENV FORGE_BASE_URL=${FORGE_BASE_URL:-https://api.example.com}
ENV MODEL=${MODEL:-test-model}
ENV AI_TEMPERATURE=${AI_TEMPERATURE:-0.7}
ENV ANTHROPIC_BASE_URL=${ANTHROPIC_BASE_URL:-https://api.example.com}
ENV ANTHROPIC_AUTH_TOKEN=${ANTHROPIC_AUTH_TOKEN:-test_token}
ENV ANTHROPIC_MODEL=${ANTHROPIC_MODEL:-test-model}
ENV ANTHROPIC_SMALL_FAST_MODEL=${ANTHROPIC_SMALL_FAST_MODEL:-test-model}
ENV OPENAI_BASE_URL=${OPENAI_BASE_URL:-https://api.example.com}
ENV OPENAI_API_KEY=${OPENAI_API_KEY:-test_key}
ENV TAVILY_API_KEY=${TAVILY_API_KEY:-test_key}
ENV GITHUB_TOKEN=${GITHUB_TOKEN:-test_token}
ENV PYTHONPATH=/app

WORKDIR /app

# Copy the entire repository
COPY . .

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install project in editable mode (CRITICAL)
RUN pip install --upgrade pip wheel

# First install the project itself
RUN pip install -e .

# Then install test dependencies
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio \
    "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Install any additional requirements if they exist
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
RUN if [ -f requirements-dev.txt ]; then pip install -r requirements-dev.txt; fi
RUN if [ -f requirements-test.txt ]; then pip install -r requirements-test.txt; fi

# For multi-package layouts, install sub-packages
RUN if [ -d libs ]; then \
    find libs -name "pyproject.toml" -o -name "setup.py" | while read pkg; do \
        pkg_dir=$(dirname "$pkg"); \
        pip install -e "$pkg_dir"; \
    done; \
fi

# Set PYTHONPATH for multi-package layouts
RUN if [ -d libs ]; then \
    export PYTHONPATH=$(find libs -type d -name "__pycache__" -prune -o -type d -print | \
        grep -E "(src|libs)" | tr '\n' ':' | sed 's/:$//'); \
    echo "export PYTHONPATH=\$PYTHONPATH:$PYTHONPATH" >> /etc/profile; \
fi

# Preflight import check
RUN python -c "import pytest; print('Preflight check passed')"

CMD ["/bin/bash"]