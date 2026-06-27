FROM python:3.12-slim AS test_builder

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

WORKDIR /app

# Install system dependencies required for some Python packages (e.g., pdfplumber, cairosvg)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    libxml2-dev \
    libxslt1-dev \
    libmagic1 \
    poppler-utils \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libfontconfig1 \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and wheel
RUN python -m pip install --upgrade pip wheel

# Copy the entire repository
COPY . .

# CRITICAL: Install the local project in editable mode unconditionally
RUN pip install -e .

# CRITICAL: Install test dependencies
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# CRITICAL: Handle multi-package layouts by setting PYTHONPATH
# Check for common package structures and add them to PYTHONPATH
ENV PYTHONPATH=/app:/app/src:/app/lib:/app/libs:/app/packages:$PYTHONPATH

# CRITICAL: Install any sub-packages found in common multi-package layouts
RUN if [ -d "/app/libs" ]; then \
        find /app/libs -name "pyproject.toml" -o -name "setup.py" | while read f; do \
            dir=$(dirname "$f"); \
            echo "Installing sub-package from $dir"; \
            pip install -e "$dir"; \
        done; \
    fi

RUN if [ -d "/app/packages" ]; then \
        find /app/packages -name "pyproject.toml" -o -name "setup.py" | while read f; do \
            dir=$(dirname "$f"); \
            echo "Installing sub-package from $dir"; \
            pip install -e "$dir"; \
        done; \
    fi

# Preflight import check to verify core modules
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Default command (as per test harness requirement)
CMD ["/bin/bash"]