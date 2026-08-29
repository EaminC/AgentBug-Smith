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

# Set environment variables for Forge API compatibility (deduplicated and corrected)
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV FORGE_API_KEY="forge-key"

WORKDIR /app

# Install system dependencies for Python build and runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev libxml2-dev libxslt1-dev python3-dev \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m pip install --upgrade pip setuptools wheel

# Copy entire repository to /app
COPY . .

# Install Python dependencies robustly:
# 1. If requirements.txt exists, install it
# 2. Else if pyproject.toml & poetry.lock exist, install poetry and then install deps
# 3. Else if only pyproject.toml exists, install carefully
# Also install editable package and test dependencies unconditionally to avoid import errors
RUN if [ -f "requirements.txt" ]; then \
        pip install -r requirements.txt; \
    fi && \
    if [ -f "pyproject.toml" ] && [ -f "poetry.lock" ]; then \
        pip install poetry && \
        poetry install; \
    fi && \
    pip install -e . && \
    pip install pytest pytest-mock pytest-xdist pytest-timeout litellm "setuptools<=81.0.0"

# If the repo has sub-packages under libs/ or packages/, install them editable too
# (Assuming common monorepo layout; adjust paths if needed)
RUN if [ -d "libs" ]; then \
        for d in libs/*; do \
            if [ -f "$d/setup.py" ] || [ -f "$d/pyproject.toml" ]; then \
                pip install -e "$d"; \
            fi; \
        done; \
    fi

# Set PYTHONPATH to include /app and all libs subdirectories for multi-package imports
ENV PYTHONPATH=/app:$(find /app/libs -type d -exec echo -n {}: \;)

# Preflight sanity check
RUN python3 -c 'import pkg_resources, pytest; print("preflight ok")'

CMD ["/bin/bash"]