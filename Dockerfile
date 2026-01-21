FROM python:3.13-alpine

# Install system dependencies
RUN apk add --no-cache \
    ffmpeg \
    gcc \
    musl-dev \
    linux-headers

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY manage_playlist.py .
COPY .env.example .

# Create directories for data persistence
RUN mkdir -p /app/downloads /app/data

# Environment variables with defaults
ENV CREDENTIALS_FILE=/app/data/client_secret.json \
    TOKEN_FILE=/app/data/token.json \
    DOWNLOAD_PATH=/app/downloads \
    POLL_INTERVAL=5

# Volume for persistent data (credentials, tokens, downloads)
VOLUME ["/app/downloads", "/app/data"]

# Run the application
ENTRYPOINT ["python", "manage_playlist.py"]

# Default to daemon mode
CMD ["--daemon"]
