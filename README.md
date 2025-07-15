# HTTP Proxy API (Python)

Generic HTTP proxy API with optional upstream proxy support for caching and routing.

## Features

- ✅ Generic HTTP proxy for any application
- ✅ Upstream proxy integration with SSL bumping support  
- ✅ No fallback - fails when upstream proxy is required but inaccessible
- ✅ Cache hit/miss detection and logging
- ✅ CORS headers for web compatibility
- ✅ Range request support for partial content requests
- ✅ Health check endpoint with upstream proxy status

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Proxy

```bash
python proxy.py
```

### 3. Configure Environment (Optional)

```bash
export UPSTREAM_PROXY_URL=http://192.168.1.79:3128
export USE_UPSTREAM=true
export PORT=8080
```

## Environment Variables

- `UPSTREAM_PROXY_URL` - Upstream proxy URL (default: http://192.168.1.79:3128)
- `USE_UPSTREAM` - Enable/disable upstream proxy (default: true)
- `PORT` - Server port (default: 8080)

## Usage

### Test Health Check
```bash
curl http://localhost:8080/health
```

### Proxy HTTP URL
```bash
curl "http://localhost:8080/proxy?url=https%3A//example.com/file.mp4"
```

## Architecture

```
Client → HTTP Proxy → Upstream Cache/Proxy → Internet
```

## Logging

The proxy uses emoji-prefixed logging for easy identification:

- 📡 Proxy requests
- 🔄 Upstream proxy operations  
- 🎯 Cache hits
- ❄️ Cache misses
- ✅ Successful operations
- ❌ Errors
- 🔒 SSL verification using system truststore

## SSL Certificate Handling

The proxy uses Python's system truststore for all SSL connections. For upstream proxies with custom certificates:

1. **Add the upstream proxy's certificate to your system truststore**
2. **macOS**: `sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain cert.crt`
3. **Linux**: Copy certificate to `/usr/local/share/ca-certificates/` and run `sudo update-ca-certificates`
4. **Windows**: Use `certmgr.msc` to add to "Trusted Root Certification Authorities"

This approach is more secure than disabling SSL verification entirely.

## Error Handling

- No fallback - fails completely when upstream proxy is required but inaccessible
- Detailed error logging with emoji prefixes
- Proper HTTP status code propagation
- CORS-enabled error responses