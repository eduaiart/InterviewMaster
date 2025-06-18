# Use Python 3.11 slim image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy application files
COPY . .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install \
    flask==2.3.2 \
    flask-sqlalchemy==3.0.5 \
    flask-login==0.6.2 \
    flask-dance==7.0.0 \
    werkzeug==2.3.6 \
    sqlalchemy==2.0.19 \
    psycopg2-binary==2.9.7 \
    gunicorn==21.2.0 \
    openai==0.27.8 \
    google-api-python-client==2.95.0 \
    google-auth-httplib2==0.1.0 \
    google-auth-oauthlib==1.0.0 \
    python-dateutil==2.8.2 \
    pytz==2023.3 \
    requests==2.31.0 \
    email-validator==2.0.0 \
    pyjwt==2.8.0 \
    sendgrid==6.10.0 \
    twilio==8.5.0

# Create necessary directories
RUN mkdir -p uploads static/css static/js

# Expose port
EXPOSE 8080

# Run the application
CMD exec gunicorn --bind :$PORT --workers 2 --timeout 120 --keep-alive 2 main:app