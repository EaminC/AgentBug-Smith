# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy only requirements first for caching
COPY requirements.txt ./

# Install dependencies if requirements.txt exists
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

# Copy the entire repository
COPY . .

# Install all local packages in editable mode (adjust paths as per repo layout)
# Assuming a multi-package repo with libs/langgraph, libs/prebuilt, libs/sdk-py as example
RUN pip install --no-cache-dir -e . \
    -e libs/langgraph \
    -e libs/prebuilt \
    -e libs/sdk-py

# Set PYTHONPATH to include all source directories for multi-package imports
ENV PYTHONPATH=/app/libs/langgraph:/app/libs/prebuilt:/app/libs/sdk-py:/app

# Default command to run tests with pytest
CMD ["pytest", "--maxfail=1", "--disable-warnings", "-q"]