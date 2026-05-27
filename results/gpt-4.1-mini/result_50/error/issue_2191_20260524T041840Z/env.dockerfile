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

# Set Forge API environment variables for OpenAI and Anthropic compatibility
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co \
    ANTHROPIC_AUTH_TOKEN=forge-key

WORKDIR /app

# Upgrade pip and setuptools
RUN python -m pip install --upgrade pip setuptools wheel

# Copy entire repository
COPY . .

# Install dependencies robustly and install local packages in editable mode unconditionally
RUN if [ -f "requirements.txt" ]; then \
        pip install -r requirements.txt; \
    fi && \
    pip install -e . && \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio pytest-xdist pytest-timeout "setuptools<=81.0.0" litellm mem0ai

# If there are sub-packages in libs/ or packages/, install them editable and set PYTHONPATH accordingly
# (Assuming typical multi-package layout; adjust paths if different)
RUN if [ -d "libs" ]; then \
        for d in libs/*; do \
            if [ -f "$d/setup.py" ] || [ -f "$d/pyproject.toml" ]; then \
                pip install -e "$d"; \
            fi; \
        done; \
    fi

ENV PYTHONPATH=/app:/app/libs:/app/packages

# Preflight test to verify essential packages
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Use bash as the default command
CMD ["/bin/bash"]