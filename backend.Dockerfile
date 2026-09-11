# ==============================================================================
# Production Dockerfile for FastAPI Backend Service
# Multi-tier multimodal research engine powered by Google Gemini 3.6 Flash
# ==============================================================================

FROM python:3.12-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered output for real-time logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8000

# Install runtime system dependencies for health checks and network security
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Create a secure non-root system user and group
RUN groupadd -g 10001 appuser && \
    useradd -u 10001 -g appuser -m -d /home/appuser -s /bin/bash appuser

# Leverage layer caching: install Python dependencies first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code and runtime configurations
COPY src/ ./src/
COPY lib/ ./lib/

# Pre-create logs directory with proper ownership for structured file sinks
RUN mkdir -p /app/logs && chown -R appuser:appuser /app

# Switch to unprivileged non-root user
USER appuser

# Expose backend REST API port
EXPOSE 8000

# Container healthcheck using backend /health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start FastAPI application using production Uvicorn ASGI server
CMD ["uvicorn", "src.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
