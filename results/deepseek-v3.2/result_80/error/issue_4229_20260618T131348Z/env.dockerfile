# branch: python/requirements.txt
FROM python:3.11-slim

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

# Set additional environment variables for Forge API compatibility
ENV AI_MAX_TOKENS="1000"
ENV AI_TOP_P="1"
ENV AI_FREQUENCY_PENALTY="0"
ENV AI_PRESENCE_PENALTY="0"

# Python environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PYTHONPATH=/app

WORKDIR /app

# Copy entire repository
COPY . .

# Create README.md if it doesn't exist (excluded by .dockerignore)
RUN if [ ! -f "README.md" ]; then echo "# AutoGPT\n\nAn open-source attempt to make GPT-4 autonomous" > README.md; fi

# Upgrade pip and install setuptools/wheel
RUN python -m pip install --upgrade pip wheel "setuptools<=81.0.0"

# Install core dependencies (skip problematic ones)
# Create a minimal requirements file without spacy, en-core-web-sm, etc.
RUN printf 'beautifulsoup4>=4.12.2\ncolorama==0.4.6\ndistro==1.8.0\nopenai==0.27.2\npython-dotenv==1.0.0\npyyaml==6.0\nreadability-lxml==0.8.1\nrequests\ntiktoken==0.3.3\ndocker\nduckduckgo-search>=2.9.5\ngoogle-api-python-client\npinecone-client==2.2.1\nredis\norjson==3.8.10\nPillow\nselenium==4.1.4\nwebdriver-manager\njsonschema\ntweepy\nclick\ncharset-normalizer>=3.1.0\ngitpython==3.1.31\nauto-gpt-plugin-template\n' > /tmp/minimal_requirements.txt

# Install minimal requirements
RUN pip install --break-system-packages -r /tmp/minimal_requirements.txt

# Install test dependencies
RUN pip install --break-system-packages \
    pytest \
    pytest-asyncio \
    pytest-mock \
    pytest-cov

# Install AI SDKs for Forge API compatibility
RUN pip install --break-system-packages \
    litellm \
    "anthropic>=0.25.0"

# CRITICAL: Install the project in editable mode
RUN pip install --break-system-packages -e .

# Instead of editable install, just set PYTHONPATH to include the project
# This avoids hatchling build issues
ENV PYTHONPATH="/app:/app/autogpt:${PYTHONPATH}"

# Simple verification
RUN python -c "import sys; print('Python', sys.version)"
RUN python -c "import pytest; print('pytest ok')"
# Verify auto_gpt_plugin_template is installed
RUN python -c "import auto_gpt_plugin_template; print('auto_gpt_plugin_template ok')"
# Verify autogpt can be imported
RUN python -c "import autogpt; print('autogpt ok')"

# Final command (required for test harness)
CMD ["/bin/bash"]