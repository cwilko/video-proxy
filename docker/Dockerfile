# Multi-stage build for optimal Alpine-based image size
FROM python:3.11-alpine AS builder

# Install build dependencies
RUN apk add --no-cache gcc musl-dev libffi-dev

# Set working directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-alpine AS production

# Install dumb-init for proper signal handling
RUN apk add --no-cache dumb-init curl

# Create non-root user
RUN addgroup -g 1001 -S proxy && \
    adduser -S proxy -u 1001

# Set working directory
WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /root/.local /home/proxy/.local

# Copy application source code
COPY --chown=proxy:proxy proxy.py ./

# Create logs directory with proper permissions
RUN mkdir -p /app/logs && chown -R proxy:proxy /app/logs

# Switch to non-root user
USER proxy

# Make sure scripts in .local are usable
ENV PATH=/home/proxy/.local/bin:$PATH

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Use dumb-init to handle signals properly
ENTRYPOINT ["dumb-init", "--"]

# Start the application
CMD ["python", "proxy.py"]