FROM python:3.11-slim

# Install development dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    make \
    gcc \
    g++ \
    postgresql-client \
    libpq-dev \
    vim \
    ssh \
    htop \
    jq \
    less \
    procps \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# Install Python development tools
RUN pip install --no-cache-dir --upgrade pip \
    black \
    flake8 \
    mypy \
    isort \
    pytest \
    pytest-cov \
    pytest-asyncio \
    pytest-xdist \
    ipython \
    httpx

# Keep Python from generating .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
# Turn off buffering for easier container logging
ENV PYTHONUNBUFFERED=1
# Set Python path to include the app directory
ENV PYTHONPATH=/app

# Entry command that keeps container running for VS Code
CMD ["sleep", "infinity"]