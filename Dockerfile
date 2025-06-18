# Use Python 3.11 slim image for better security and smaller size
FROM python:3.11-slim

# Set environment variables for Python optimization
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Install system dependencies including PostgreSQL client
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Upgrade pip and install build tools
RUN pip install --upgrade pip setuptools wheel

# Copy requirements and install Python dependencies
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir -e .

# Create necessary directories with proper permissions
RUN mkdir -p uploads static/css static/js templates \
    && chown -R appuser:appuser /app

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Expose port (Google Cloud Run uses PORT environment variable)
EXPOSE 8080

# Set production environment variables
ENV FLASK_ENV=production \
    FLASK_APP=main.py \
    PORT=8080 \
    WORKERS=2 \
    TIMEOUT=120 \
    MAX_REQUESTS=1000 \
    MAX_REQUESTS_JITTER=100

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:$PORT/health || exit 1

# Add health check endpoint (we'll create this route)
# Run the application with optimized settings for Google Cloud
CMD exec gunicorn \
    --bind 0.0.0.0:$PORT \
    --workers $WORKERS \
    --worker-class sync \
    --timeout $TIMEOUT \
    --keep-alive 2 \
    --max-requests $MAX_REQUESTS \
    --max-requests-jitter $MAX_REQUESTS_JITTER \
    --preload \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    main:app