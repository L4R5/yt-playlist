FROM python:3.13-alpine

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app.py .
COPY templates templates/

# Create non-root user
RUN adduser -D -u 1000 authuser && \
    chown -R authuser:authuser /app

USER authuser

EXPOSE 5000

CMD ["python", "app.py"]
