# Use official Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies first
# (This layer is cached by Docker — speeds up rebuilds)
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Create a non-root user for security
RUN adduser --disabled-password --gecos '' appuser \
    && chown -R appuser /app
USER appuser

# Expose port 5000
EXPOSE 5000

# Health check — Docker will ping /health every 30 seconds
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/health')" || exit 1

# Run app with gunicorn (production server, 4 workers)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--access-logfile", "-", "app:app"]
