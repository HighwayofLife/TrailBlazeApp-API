FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Add app directory to Python path
ENV PYTHONPATH="${PYTHONPATH}:/app"

# Create directories needed by the app
RUN mkdir -p logs cache tests/temp_cache tests/metrics

# Run tests during build to verify everything is working (optional)
# RUN python -m pytest

# Default command (can be overridden)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]