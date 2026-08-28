FROM python:3.12-slim AS test_builder

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="openai/tuzi-deepseek-v3.2/deepseek-v3.2"
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

# Set working directory
WORKDIR /app

# Copy entire repo
COPY . .

# Upgrade pip, setuptools, wheel early
RUN python -m pip install --upgrade pip setuptools wheel

# Install dependencies and project, robust logic
RUN if [ -f "requirements.txt" ]; then \
      pip install -r requirements.txt && pip install -e . && \
      pip install pytest pytest-mock pytest-xdist pytest-timeout "setuptools<=81.0.0" litellm mem0ai; \
    elif [ -f "pyproject.toml" ] && [ -f "poetry.lock" ]; then \
      pip install poetry && poetry install && pip install -e . && \
      pip install pytest pytest-mock pytest-xdist pytest-timeout "setuptools<=81.0.0" litellm mem0ai; \
    elif [ -f "pyproject.toml" ]; then \
      pip install -e . && \
      pip install pytest pytest-mock pytest-xdist pytest-timeout "setuptools<=81.0.0" litellm mem0ai; \
    else \
      pip install -e . && \
      pip install pytest pytest-mock pytest-xdist pytest-timeout "setuptools<=81.0.0" litellm mem0ai; \
    fi

# Preflight check to verify importability
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Default command
CMD ["/bin/bash"]