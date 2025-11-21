# OpenBenchVue Docker Container
# Multi-stage build for optimized image size

# Stage 1: Builder
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libusb-1.0-0-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libusb-1.0-0 \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create application user
RUN useradd -m -u 1000 openbench && \
    mkdir -p /app /data && \
    chown -R openbench:openbench /app /data

# Set working directory
WORKDIR /app

# Copy application files
COPY --chown=openbench:openbench . /app/

# Install the application
RUN pip install --no-cache-dir -e .

# Switch to non-root user
USER openbench

# Expose ports
EXPOSE 5000

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV OPENBENCHVUE_DATA_DIR=/data

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import openbenchvue; print('OK')" || exit 1

# Default command: Run remote server
CMD ["openbenchvue", "--remote", "--remote-host", "0.0.0.0", "--remote-port", "5000"]
