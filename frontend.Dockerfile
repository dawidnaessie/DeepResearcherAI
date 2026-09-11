# ==============================================================================
# Production Dockerfile for Streamlit Frontend Dashboard
# Interactive analytical visualization suite (Mind Map, Flashcards, Timeline)
# ==============================================================================

FROM python:3.12-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered output for real-time logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8501

# Install runtime system dependencies for health checks
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

# Copy application source code and Streamlit configuration
COPY src/ ./src/
COPY lib/ ./lib/
COPY .streamlit/ ./.streamlit/

# Set proper ownership for non-root user
RUN chown -R appuser:appuser /app

# Switch to unprivileged non-root user
USER appuser

# Expose Streamlit web interface port
EXPOSE 8501

# Container healthcheck using Streamlit internal health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Start Streamlit application
CMD ["streamlit", "run", "src/frontend/app.py", "--server.address=0.0.0.0", "--server.port=8501"]
