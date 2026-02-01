FROM docker.io/library/python:3.11-slim@sha256:1dd3dca85e22886e44fcad1bb7ccab6691dfa83db52214cf9e20696e095f3e36

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY internal/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Expose port and define command
EXPOSE 8080
CMD ["python", "app.py"]
