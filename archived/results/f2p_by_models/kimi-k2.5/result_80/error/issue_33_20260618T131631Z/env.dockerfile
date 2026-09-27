FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files if they exist
COPY requirements.txt* setup.py* pyproject.toml* ./

# Install dependencies safely (conditional)
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

# Copy the entire repository
COPY . .

# Install the local package in editable mode unconditionally (CRITICAL)
RUN pip install -e .

# Set PYTHONPATH for potential monorepo layouts or src-based structures
ENV PYTHONPATH=/app/src:/app:$PYTHONPATH

# Default command to run the specific test file
CMD ["pytest", "tests/formatter_dashscope_test.py", "-v", "--tb=short"]