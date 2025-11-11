# Dockerfile for ZEUES Backend
# Simple, clean Docker deployment avoiding nixpacks complications

FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements first (better caching)
COPY backend/requirements.txt /app/backend/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r backend/requirements.txt

# Copy entire project
COPY . /app

# Set PYTHONPATH so Python can find the backend module
ENV PYTHONPATH=/app

# Expose port (Railway will use $PORT env var)
EXPOSE 8000

# Start command - use shell form to allow $PORT expansion
CMD python -m uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
