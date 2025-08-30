# Minimal production container for Twilio webhook using gunicorn
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements-test-client.txt ./
RUN pip install --no-cache-dir -r requirements-test-client.txt

COPY test_client.py ./

# Create non-root user for security
RUN groupadd -r appgroup && useradd -r -g appgroup appuser
RUN chown -R appuser:appgroup /app
USER appuser

# Env:
#   TWILIO_FROM: e.g., +15551234567 (sending number)
#   DAYLE_SERVER: base URL for local reply server
#   AUTO_REPLY: set to 1 to send via REST in addition to TwiML
#   LOG_FORMAT: json|text

EXPOSE 5005

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5005/health || exit 1

# Gunicorn factory import requires --factory flag
CMD ["gunicorn", "--workers", "2", "--threads", "4", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "info", "--bind", "0.0.0.0:5005", "--factory", "test_client:create_twilio_app_from_env"]

