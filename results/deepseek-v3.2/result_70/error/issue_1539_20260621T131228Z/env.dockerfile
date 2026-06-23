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

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    chromium \
    fonts-ipafont-gothic \
    fonts-wqy-zenhei \
    fonts-thai-tlwg \
    fonts-kacst \
    fonts-freefont-ttf \
    libxss1 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

# Set PYTHONPATH for monorepo support - scan for Python packages
RUN find /app -name "pyproject.toml" -o -name "setup.py" -o -name "setup.cfg" | \
    xargs -I {} dirname {} | sort -u > /tmp/python_dirs.txt && \
    echo "PYTHONPATH=\$(cat /tmp/python_dirs.txt | tr '\n' ':')" >> /etc/environment

# Install system dependencies first
RUN python -m pip install --upgrade pip wheel

# Install the main package in editable mode
RUN pip install -e .

# Install sub-packages if they exist (common monorepo patterns)
RUN for dir in libs packages src components modules; do \
    if [ -d "/app/$dir" ]; then \
        find "/app/$dir" -name "pyproject.toml" -o -name "setup.py" | while read -r pkg_file; do \
            pkg_dir=$(dirname "$pkg_file"); \
            echo "Installing package from $pkg_dir"; \
            pip install -e "$pkg_dir" || echo "Failed to install $pkg_dir, continuing..."; \
        done; \
    fi; \
done

# Install dependencies from requirements.txt if present
RUN if [ -f "requirements.txt" ]; then \
    pip install -r requirements.txt; \
fi

# Install test dependencies
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio litellm pytest-xdist pytest-timeout mem0ai

# Install Node.js dependencies if needed for mermaid-cli
RUN if command -v npm > /dev/null 2>&1; then \
    npm install -g @mermaid-js/mermaid-cli && npm cache clean --force; \
fi

# Set environment variables for chromium
ENV CHROME_BIN=/usr/bin/chromium \
    PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true

# Final PYTHONPATH setup combining all discovered paths
RUN find /app -type f -name "*.py" -path "*/__init__.py" | \
    xargs -I {} dirname {} | sort -u | grep -v __pycache__ > /tmp/init_dirs.txt && \
    echo "export PYTHONPATH=\$(cat /tmp/init_dirs.txt | tr '\n' ':')" >> ~/.bashrc

# Preflight import check
RUN python -c "import sys; print('Python path:', sys.path); \
    try: \
        import metagpt; \
        print('metagpt imported successfully'); \
    except ImportError as e: \
        print(f'Failed to import metagpt: {e}'); \
        print('Available modules:', [m for m in sys.modules.keys() if 'meta' in m.lower()]); \
    import pytest; \
    print('pytest imported successfully'); \
    print('preflight ok')"

CMD ["/bin/bash"]