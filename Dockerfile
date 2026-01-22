FROM python:3.13-alpine

# Install system dependencies including Node.js
RUN apk add --no-cache \
    ffmpeg \
    gcc \
    musl-dev \
    linux-headers \
    nodejs

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY manage_playlist.py .
COPY .env.example .

# Create non-root user and directories
# Note: When using volumes in Kubernetes, fsGroup will override ownership
RUN addgroup -g 1000 appgroup && \
    adduser -D -u 1000 -G appgroup appuser && \
    mkdir -p /app/downloads /app/data && \
    chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser:appgroup

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
