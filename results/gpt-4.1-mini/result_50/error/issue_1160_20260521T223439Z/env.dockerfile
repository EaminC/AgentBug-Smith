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

# Set working directory
WORKDIR /app

# Copy the entire repository into the container
COPY . .

# Upgrade pip, setuptools, and wheel
RUN python -m pip install --upgrade pip setuptools wheel

# Set environment variables for Forge API compatibility
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1" \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co" \
    ANTHROPIC_AUTH_TOKEN=forge-key

# Install dependencies and test tools
RUN if [ -f "requirements.txt" ]; then pip install -r requirements.txt; fi
RUN pip install -e . pytest pytest-mock pytest-xdist pytest-timeout anyio "setuptools<=81.0.0" litellm

# Install sub-packages in editable mode if applicable (example for multi-package repo)
# Adjust paths below if the repo has additional packages
# RUN pip install -e ./src/agentscope

# Set PYTHONPATH to include all relevant source directories for imports including mem0
ENV PYTHONPATH=/app/src:/app/src/agentscope

# Verify installation (preflight)
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Default shell command for test environment
CMD ["/bin/bash"]