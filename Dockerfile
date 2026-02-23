# DataForge Dockerfile - Secure Production Build
FROM python:3.11-slim

# Set labels for image metadata and traceability
LABEL maintainer="DataForge Team"
LABEL description="DataForge - Knowledge Base Management System with Semantic Search"
LABEL version="1.0.0"
LABEL security="production-hardened"

# Set working directory
WORKDIR /app

# Install system dependencies (minimal set for security)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* /var/tmp/*

# Create non-root user for running application (security best practice)
RUN groupadd -r dataforge && useradd -r -g dataforge dataforge

# Copy requirements and local packages for dependency install
COPY requirements.txt .
COPY forge-telemetry/ ./forge-telemetry/

# Install Python dependencies
RUN pip install --no-cache-dir ./forge-telemetry \
    && pip install --no-cache-dir -r requirements.txt \
    && pip cache purge

# Copy application code
COPY --chown=dataforge:dataforge . .

# Create necessary directories with proper permissions
RUN mkdir -p /app/static /app/templates /app/logs \
    && chown -R dataforge:dataforge /app

# Switch to non-root user
USER dataforge

# Expose port
EXPOSE 8001

# Health check - improved with curl timeout
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Set environment variables for security
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Run the application with production settings
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8001", \
     "--access-log", \
     "--log-level", "info"]
