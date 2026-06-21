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

# Set environment variables for Forge
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1
ENV ANTHROPIC_AUTH_TOKEN=forge-key
ENV PYTHONUNBUFFERED=1
# Set environment variables to satisfy test dependencies (from .github/workflows/tests.yml)
ENV BRAVE_API_KEY=fake-brave-key
ENV SNOWFLAKE_USER=fake-snowflake-user
ENV SNOWFLAKE_PASSWORD=fake-snowflake-password
ENV SNOWFLAKE_ACCOUNT=fake-snowflake-account
ENV SNOWFLAKE_WAREHOUSE=fake-snowflake-warehouse
ENV SNOWFLAKE_DATABASE=fake-snowflake-database
ENV SNOWFLAKE_SCHEMA=fake-snowflake-schema
ENV EMBEDCHAIN_DB_URI=sqlite:///test.db

# Set PYTHONPATH for monorepo layout
ENV PYTHONPATH=/app/lib/crewai:/app/lib/crewai-tools:$PYTHONPATH

WORKDIR /app

# Upgrade packaging tools early
RUN python -m pip install --upgrade pip setuptools wheel

# Copy entire repository (critical for externally injected tests)
COPY . .

# Install dependencies from pyproject.toml files if they exist
RUN if [ -f "lib/crewai/pyproject.toml" ]; then \
    cd lib/crewai && pip install -e .; \
    fi

RUN if [ -f "lib/crewai-tools/pyproject.toml" ]; then \
    cd lib/crewai-tools && pip install -e .; \
    fi

# Also try installing from root if there's a pyproject.toml
RUN if [ -f "pyproject.toml" ]; then \
    pip install -e .; \
    fi

# Install test dependencies
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai \
    pytest-subprocess vcrpy pytest-recording pytest-randomly pytest-split \
    types-requests types-pyyaml types-regex types-appdirs boto3-stubs[bedrock-runtime] types-psycopg2 types-pymysql

# Preflight import check (mandatory)
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Final command (mandatory)
CMD ["/bin/bash"]