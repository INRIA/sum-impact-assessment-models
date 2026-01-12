# Multi-stage Dockerfile for SUM Impact Assessment API
# Stage 1: Builder - prepare dependencies
FROM python:3.13-slim AS builder

WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies in a virtual environment
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime - minimal production image
FROM python:3.13-slim

WORKDIR /app

# Install runtime dependencies (curl for health checks)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Copy application code
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser run_api.py .

# Switch to non-root user
USER appuser

# Expose API port
EXPOSE 8000

# Health check using the /health endpoint
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the FastAPI application with uvicorn
CMD ["python", "-m", "uvicorn", "src.sum_impact_assessment.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
