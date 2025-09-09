FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE ${SCRAPER_INTERNAL_PORT}

# Run the application
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${SCRAPER_INTERNAL_PORT}"]