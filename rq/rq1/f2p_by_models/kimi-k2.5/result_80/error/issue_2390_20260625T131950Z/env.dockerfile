FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tuzi-kimi-k2.5/kimi-k2.5"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tuzi-kimi-k2.5/kimi-k2.5"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi-kimi-k2.5/kimi-k2.5"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

WORKDIR /app

# Install system dependencies required for browser automation and compilation (git for gitpython, browsers for selenium)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    gcc \
    chromium-driver \
    wget \
    gnupg2 \
    libgtk-3-0 \
    libdbus-glib-1-2 \
    dbus-x11 \
    xvfb \
    ca-certificates \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y chromium firefox-esr \
    && rm -rf /var/lib/apt/lists/*

# Copy entire repository to ensure injected test scripts are included
COPY . .

# Install Python dependencies and the package itself
# Assumption: requirements.txt exists as evidenced in repository files
RUN python -m pip install --upgrade pip wheel && \
    pip install -r requirements.txt && \
    pip install -e . && \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Preflight verification to ensure core modules and pytest are importable
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

CMD ["/bin/bash"]