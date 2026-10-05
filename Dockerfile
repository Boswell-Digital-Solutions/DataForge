# syntax=docker/dockerfile:1
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
# git is required because requirements.txt installs packages from git+https
# URLs; without it pip fails with "Cannot find command 'git'".
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    git \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* /var/tmp/*

# Create non-root user for running application (security best practice)
RUN groupadd -r dataforge && useradd -r -g dataforge dataforge

# Copy requirements and the private-dependency auth helper for the dependency install
COPY requirements.txt .
COPY scripts/docker-git-auth.sh /usr/local/bin/docker-git-auth.sh

# Install Python dependencies. requirements.txt pins private
# Boswell-Digital-Solutions git dependencies (forge-telemetry,
# forge_contract_core); BuildKit injects short-lived tokens via --secret
# so they never land in an image layer or build history. BUILD_AUTH_MODE picks the
# secrets: "legacy" reads `github_token`; "split" reads one secret per repository and
# fails closed (see scripts/docker-git-auth.sh). With no secret in legacy mode this is a
# no-op that falls back to the earlier failure -- see docker-build docs.
ARG BUILD_AUTH_MODE=legacy
RUN --mount=type=secret,id=github_token,required=false \
    --mount=type=secret,id=telemetry_token,required=false \
    --mount=type=secret,id=contract_core_token,required=false \
    set -eu; \
    BUILD_AUTH_MODE="$BUILD_AUTH_MODE" sh /usr/local/bin/docker-git-auth.sh; \
    python -m pip install --no-cache-dir -r requirements.txt; \
    python -m pip cache purge; \
    rm -f /root/.gitconfig

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
