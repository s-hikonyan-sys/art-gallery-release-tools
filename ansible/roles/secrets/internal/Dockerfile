FROM docker.io/library/python:3.11-slim@sha256:1dd3dca85e22886e44fcad1bb7ccab6691dfa83db52214cf9e20696e095f3e36

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY internal/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "app.py"]
