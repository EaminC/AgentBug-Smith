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

# Set working directory to repository root
WORKDIR /app

# Copy entire repository into /app
COPY . .

# Set environment variables for Forge API compatibility
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1" \
    OPENAI_API_KEY="forge-key" \
    ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co" \
    ANTHROPIC_AUTH_TOKEN="forge-key"

# If the repo has multiple packages, install all editable packages unconditionally
# Detect sub-packages by presence of setup.py or pyproject.toml in subdirs libs/, packages/, or root
# For safety, install root and libs/* if exist

RUN python -m pip install --upgrade pip setuptools wheel

# Install editable packages and dependencies
RUN if [ -f "requirements.txt" ]; then \
      pip install -r requirements.txt; \
    fi && \
    pip install -e . && \
    if [ -d "libs" ]; then \
      for d in libs/*; do \
        if [ -f "$d/setup.py" ] || [ -f "$d/pyproject.toml" ]; then \
          pip install -e "$d"; \
        fi; \
      done; \
    fi && \
    pip install pytest pytest-mock pytest-xdist pytest-timeout "setuptools<=81.0.0" litellm

# Explicitly set PYTHONPATH to include root and libs/* if exist
ENV PYTHONPATH=/app
RUN if [ -d "libs" ]; then \
      export PYTHONPATH=$PYTHONPATH:$(find libs -maxdepth 1 -type d -exec echo /app/{} \| tr '\n' ':'); \
    fi

# Verify installation by importing important packages
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Default command for container (required for test harness)
CMD ["/bin/bash"]

# branch: python/requirements-or-pyproject