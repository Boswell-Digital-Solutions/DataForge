FROM python:3.11-slim

WORKDIR /app

# Install Rust build tools (for maturin develop)
RUN apt-get update && apt-get install -y \
    cargo \
    rustc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy workspace
COPY . .

# Install Python dependencies and build Rust extensions
RUN pip install --no-cache-dir -e .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Run server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
