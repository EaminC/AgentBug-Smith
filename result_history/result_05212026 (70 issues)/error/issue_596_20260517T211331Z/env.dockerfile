FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tensorblock/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV GITHUB_TOKEN="ghp_key"
ENV TAVILY_API_KEY="tvly_key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tensorblock/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="tensorblock/gpt-4.1-mini"
ENV OPENAI_API_KEY="forge-key"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
# --- end inject ---

# Set environment variables for Forge API compatibility with OpenAI and Anthropic SDKs
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1" \
    OPENAI_API_KEY="forge-key" \
    ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1" \
    ANTHROPIC_AUTH_TOKEN="forge-key"

WORKDIR /app

COPY . .

# Install system dependencies needed for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential python3-dev gcc libffi-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and setuptools (bounded version) and wheel
RUN python -m pip install --upgrade pip
RUN python -m pip install "setuptools<=81.0.0" wheel

# Install Python dependencies and editable install, including test dependencies
RUN if [ -f "requirements.txt" ]; then \
    pip install -r requirements.txt; \
fi && \
pip install -e . && \
pip install pytest pytest-mock pytest-xdist pytest-timeout litellm

# If repository has sub-packages, install them editable and set PYTHONPATH
# (Adjust these paths if your repo has other package dirs)
RUN if [ -d "libs/langgraph" ]; then pip install -e libs/langgraph; fi
RUN if [ -d "libs/prebuilt" ]; then pip install -e libs/prebuilt; fi
RUN if [ -d "libs/sdk-py" ]; then pip install -e libs/sdk-py; fi

ENV PYTHONPATH=/app/libs/langgraph:/app/libs/prebuilt:/app/libs/sdk-py

# Preflight to verify installation
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

CMD ["/bin/bash"]