# FastAPI Backend Dockerfile
# Using full python image (not slim) to avoid numpy/scipy compilation issues
FROM python:3.13-bookworm

WORKDIR /app

# Install system dependencies for PDF processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ ./backend/
COPY data/ ./data/

# Create necessary directories (tmp is runtime-only, not copied)
RUN mkdir -p data/raw_pdfs tmp

# Expose port
EXPOSE 8000

# Run the FastAPI application
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
