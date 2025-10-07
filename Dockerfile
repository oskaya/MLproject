# Guard Vision V2 - Security Monitoring System
# Multi-stage Docker build for production deployment

# Stage 1: Build stage
FROM python:3.11-slim as builder

# Set work directory
WORKDIR /app

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    python3-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Production stage
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    FLASK_APP=main.py

# Create non-root user for security
RUN groupadd -r guardvision && useradd -r -g guardvision guardvision

# Set work directory
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder stage
COPY --from=builder /root/.local /home/guardvision/.local

# Make sure scripts in .local are usable
ENV PATH=/home/guardvision/.local/bin:$PATH

# Copy application code
COPY --chown=guardvision:guardvision . .

# Make entrypoint script executable
RUN chmod +x entrypoint.sh

# Create directories for logs and data
RUN mkdir -p /app/logs /app/data && \
    chown -R guardvision:guardvision /app

# Switch to non-root user
USER guardvision

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/api/camera/status || exit 1

# Run the application
CMD ["./entrypoint.sh"]