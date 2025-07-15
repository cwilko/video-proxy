# Docker Configuration for Video Proxy Python

This directory contains Docker configuration for the Python HTTP proxy service.

## Quick Start

### Build the image locally:
```bash
docker build -t video-proxy-python .
```

### Run with docker-compose (recommended):
```bash
docker-compose up -d
```

### Run the container directly:
```bash
docker run -d \
  --name video-proxy-python \
  --restart unless-stopped \
  -p 8080:8080 \
  video-proxy-python
```

### Run with custom configuration:
```bash
docker run -d \
  --name video-proxy-python \
  --restart unless-stopped \
  -p 8080:8080 \
  -e UPSTREAM_PROXY_URL=http://192.168.1.100:3128 \
  -e USE_UPSTREAM=true \
  video-proxy-python
```

## Image Details

- **Base Image**: `python:3.11-alpine` (minimal size)
- **Multi-stage build**: Optimized for production deployment
- **Security**: Runs as non-root user (UID 1001)
- **Health Check**: Built-in health monitoring
- **Signal handling**: Proper shutdown with dumb-init

## Environment Variables

The proxy can be configured using environment variables:

- `PORT`: Server port (default: 8080)
- `UPSTREAM_PROXY_URL`: Upstream proxy URL (default: http://192.168.1.79:3128)
- `USE_UPSTREAM`: Enable/disable upstream proxy (default: true)

## Docker Compose

The included `docker-compose.yml` provides:

- **Main service**: video-proxy-python
- **Health checks**: Automatic health monitoring
- **Volume mounts**: Persistent logs
- **Test service**: Optional test client (use `--profile test`)

### Running with test client:
```bash
docker-compose --profile test up -d
```

## Production Deployment

### Basic deployment:
```bash
# Pull/build latest image
docker-compose pull || docker-compose build

# Run in production mode
docker-compose up -d

# Check status
docker-compose ps
docker-compose logs -f video-proxy-python
```

### With custom upstream proxy:
```bash
# Create environment file
cat > .env << EOF
UPSTREAM_PROXY_URL=http://your-proxy:3128
USE_UPSTREAM=true
PORT=8080
EOF

# Run with environment file
docker-compose up -d
```

### Without upstream proxy:
```bash
docker run -d \
  --name video-proxy-python \
  --restart unless-stopped \
  -p 8080:8080 \
  -e USE_UPSTREAM=false \
  video-proxy-python
```

## Health Monitoring

The container includes a built-in health check:

```bash
# Check health status
docker inspect --format='{{.State.Health.Status}}' video-proxy-python

# Manual health check
curl http://localhost:8080/health
```

## Volume Mounts

### Persistent logs:
```bash
docker run -d \
  --name video-proxy-python \
  -p 8080:8080 \
  -v /path/to/logs:/app/logs \
  video-proxy-python
```

## Security Features

- **Non-root user**: Runs as UID 1001
- **Minimal Alpine base**: Reduced attack surface
- **Multi-stage build**: No build tools in production image
- **Health monitoring**: Automatic failure detection
- **Proper signal handling**: Clean shutdown support

## Testing

### Test the proxy functionality:
```bash
# Basic health check
curl http://localhost:8080/health

# Test proxy with a simple request
curl -X GET "http://localhost:8080/proxy?url=https%3A%2F%2Fhttpbin.org%2Fget"

# Test with docker-compose test client
docker-compose --profile test up -d
docker-compose exec test-client curl http://video-proxy-python:8080/health
```

## Troubleshooting

### Check container logs:
```bash
docker logs video-proxy-python
# or with docker-compose
docker-compose logs video-proxy-python
```

### Check health status:
```bash
docker inspect --format='{{.State.Health.Status}}' video-proxy-python
```

### Access container shell:
```bash
docker exec -it video-proxy-python sh
```

### Common issues:

1. **Port already in use**: Change port mapping `-p 8081:8080`
2. **Upstream proxy unreachable**: Set `USE_UPSTREAM=false` or fix proxy URL
3. **Permission issues**: Check volume mount permissions

## Building for Multiple Architectures

```bash
# Build for multiple platforms
docker buildx create --name multiarch --use
docker buildx build --platform linux/amd64,linux/arm64 -t your-registry/video-proxy-python:latest --push .
```

## Integration with Squirrel Stream

This proxy is designed to work with the Squirrel Stream addon:

```bash
# Run both services
docker-compose up -d

# The proxy will be available at http://localhost:8080
# Configure Squirrel Stream to use: proxy=http%3A%2F%2Flocalhost%3A8080
```

## Monitoring and Logging

Logs are written to `/app/logs/` inside the container:

```bash
# View logs
docker-compose exec video-proxy-python cat /app/logs/proxy.log

# Or mount logs directory
docker run -v ./logs:/app/logs video-proxy-python
```