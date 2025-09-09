FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create model cache directory
RUN mkdir -p /app/models

EXPOSE ${RAG_API_INTERNAL_PORT}

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${RAG_API_INTERNAL_PORT} --reload"]