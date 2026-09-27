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

# Copy entire repository
COPY . .

# Upgrade pip, setuptools, wheel early
RUN python -m pip install --upgrade pip setuptools wheel

# Install dependencies from requirements.txt if it exists, then install the package itself and test dependencies
RUN if [ -f "requirements.txt" ]; then \
      pip install -r requirements.txt; \
    fi && \
    pip install -e . && \
    pip install pytest pytest-mock pytest-asyncio pytest-cov pytest-timeout anyio "setuptools<=81.0.0" litellm

# If repository has sub-packages (common in monorepos), install them editable too
# (Adjust these paths if your repo structure differs)
RUN if [ -d "libs/langgraph" ]; then pip install -e libs/langgraph; fi
RUN if [ -d "libs/prebuilt" ]; then pip install -e libs/prebuilt; fi
RUN if [ -d "libs/sdk-py" ]; then pip install -e libs/sdk-py; fi

# Set PYTHONPATH to include all relevant source directories for multi-package repo
ENV PYTHONPATH=/app:/app/libs/langgraph:/app/libs/prebuilt:/app/libs/sdk-py

# Set environment variables for Forge API compatibility (OpenAI and Anthropic compatible)
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"

# Mandatory to have FORGE_API_KEY available as well
ENV FORGE_API_KEY="forge-key"

# Verify core packages and pytest imports
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Default CMD: interactive bash shell at repo root (test harness requirement)
CMD ["/bin/bash"]