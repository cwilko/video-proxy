#!/usr/bin/env python3
"""
HTTP Proxy API - Python version
Generic HTTP proxy with optional upstream proxy support
"""

import os
import asyncio
import aiohttp
from aiohttp import web, ClientSession, ClientTimeout
import urllib.parse
import json
import logging
from datetime import datetime
import ssl

# Configuration
PORT = int(os.getenv('PORT', 8080))
UPSTREAM_PROXY_URL = os.getenv('UPSTREAM_PROXY_URL', 'http://192.168.1.79:3128')
USE_UPSTREAM = os.getenv('USE_UPSTREAM', 'true').lower() != 'false'

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def log_with_emoji(emoji, message):
    """Log with emoji prefix"""
    logger.info(f"{emoji} {message}")

# SSL context for direct connections (when not using upstream proxy)
ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
ssl_context.load_default_certs()  # Load system certificates

async def proxy_handler(request):
    """Handle proxy requests (GET and HEAD)"""
    try:
        # Handle HEAD requests differently
        is_head_request = request.method == 'HEAD'
        target_url = request.query.get('url')
        user_agent = request.headers.get('User-Agent', 'Unknown')
        
        log_with_emoji('📡', f"Proxy request received from: {user_agent}")
        log_with_emoji('🔗', f"Target URL: {target_url[:100] + '...' if target_url and len(target_url) > 100 else target_url or 'MISSING'}")
        
        if not target_url:
            log_with_emoji('❌', "Missing URL parameter")
            return web.json_response({'error': 'Missing url parameter'}, status=400)
        
        decoded_url = urllib.parse.unquote(target_url)
        log_with_emoji('🎯', f"Proxying request to: {decoded_url}")
        
        if USE_UPSTREAM:
            log_with_emoji('🔄', f"Routing through upstream proxy: {UPSTREAM_PROXY_URL}")
        
        # Prepare headers
        headers = {
            'User-Agent': request.headers.get('User-Agent', 'Mozilla/5.0 (compatible; HTTPProxy/1.0)'),
        }
        
        # Add cache-friendly headers if using upstream proxy
        if USE_UPSTREAM:
            headers['Cache-Control'] = 'max-age=3600'
        
        # Forward Range header for partial content requests
        if 'Range' in request.headers:
            headers['Range'] = request.headers['Range']
            log_with_emoji('📊', f"Range request: {request.headers['Range']}")
        
        # Forward Referer if present
        if 'Referer' in request.headers:
            headers['Referer'] = request.headers['Referer']
        
        # Setup connector and session 
        connector_kwargs = {}
        
        # Configure proxy if using upstream proxy
        proxy = UPSTREAM_PROXY_URL if USE_UPSTREAM else None
        
        if USE_UPSTREAM and proxy:
            # For upstream proxy connections, disable SSL verification
            # since the upstream proxy handles SSL termination
            connector_kwargs['ssl'] = False
        else:
            # For direct connections, use system truststore
            connector_kwargs['ssl'] = ssl_context
        
        connector = aiohttp.TCPConnector(**connector_kwargs)
        timeout = ClientTimeout(total=30)
        
        async with ClientSession(
            connector=connector,
            timeout=timeout,
            headers=headers
        ) as session:
            
            try:
                # Use HEAD for HEAD requests, GET for GET requests
                method = session.head if is_head_request else session.get
                async with method(decoded_url, proxy=proxy, allow_redirects=True) as response:
                    if response.status >= 400:
                        log_with_emoji('❌', f"Upstream error: {response.status} {response.reason}")
                        return web.json_response({
                            'error': f'Upstream error: {response.status} {response.reason}'
                        }, status=response.status)
                    
                    # Create response
                    resp = web.StreamResponse(status=response.status)
                    
                    # Forward important headers
                    headers_to_forward = [
                        'content-type', 'content-length', 'content-range',
                        'accept-ranges', 'last-modified', 'etag',
                        'cache-control', 'expires'
                    ]
                    
                    for header in headers_to_forward:
                        if header in response.headers:
                            resp.headers[header] = response.headers[header]
                    
                    # Add CORS headers
                    resp.headers['Access-Control-Allow-Origin'] = '*'
                    resp.headers['Access-Control-Allow-Headers'] = 'Origin, X-Requested-With, Content-Type, Accept, Range, User-Agent'
                    resp.headers['Access-Control-Allow-Methods'] = 'GET, HEAD, OPTIONS'
                    resp.headers['Access-Control-Expose-Headers'] = 'Content-Range, Content-Length, Accept-Ranges'
                    
                    # Check for cache hits/misses from upstream proxy
                    x_cache = response.headers.get('x-cache') or response.headers.get('x-cache-lookup')
                    cache_status = '🔍 Cache status unknown'
                    if x_cache:
                        cache_status = '🎯 CACHE HIT' if 'HIT' in x_cache else '❄️ CACHE MISS'
                    
                    # Log response info
                    log_with_emoji('✅', f"Response: {response.status} {response.reason}")
                    log_with_emoji('📝', f"Content-Type: {response.headers.get('content-type', 'unknown')}")
                    log_with_emoji('📏', f"Content-Length: {response.headers.get('content-length', 'unknown')}")
                    
                    if USE_UPSTREAM:
                        log_with_emoji('🔄', cache_status)
                    
                    if 'content-range' in response.headers:
                        log_with_emoji('📊', f"Content-Range: {response.headers['content-range']}")
                    
                    # Log cache-related headers
                    if 'age' in response.headers:
                        log_with_emoji('⏰', f"Cache Age: {response.headers['age']} seconds")
                    if 'x-cache' in response.headers:
                        log_with_emoji('🏷️', f"X-Cache: {response.headers['x-cache']}")
                    
                    # Prepare response
                    await resp.prepare(request)
                    
                    # For HEAD requests, don't stream content
                    if not is_head_request:
                        try:
                            async for chunk in response.content.iter_chunked(8192):
                                await resp.write(chunk)
                        except (ConnectionResetError, BrokenPipeError, asyncio.CancelledError) as e:
                            # Client disconnected - this is normal for video streaming
                            logger.debug(f"Client disconnected during streaming: {e}")
                            return resp
                        except Exception as e:
                            if "closing transport" in str(e).lower() or "connection" in str(e).lower():
                                logger.debug(f"Connection closed during streaming: {e}")
                                return resp
                            raise
                    
                    await resp.write_eof()
                    return resp
                    
            except Exception as proxy_error:
                # Don't log common streaming disconnection errors as errors
                if any(term in str(proxy_error).lower() for term in ['closing transport', 'connection reset', 'broken pipe']):
                    logger.debug(f"Connection closed during proxy operation: {proxy_error}")
                    # Return without error response for normal disconnections
                    return web.Response(status=499)  # Client closed request
                
                # Log the actual error
                log_with_emoji('❌', f"Proxy error: {proxy_error}")
                
                # Check if it's an upstream proxy connection error
                if USE_UPSTREAM and ('proxy' in str(proxy_error).lower() or 'connection' in str(proxy_error).lower()):
                    log_with_emoji('🔄', "Upstream proxy connection failed - no fallback configured")
                    log_with_emoji('❌', "Request failed because upstream proxy is required but inaccessible")
                
                return web.json_response({
                    'error': 'Proxy request failed',
                    'details': str(proxy_error),
                    'upstreamProxy': UPSTREAM_PROXY_URL if USE_UPSTREAM else 'disabled'
                }, status=500)
                
    except Exception as e:
        log_with_emoji('❌', f"Handler error: {e}")
        return web.json_response({'error': 'Internal server error'}, status=500)


async def health_handler(request):
    """Health check with upstream proxy status"""
    upstream_status = 'disabled'
    
    if USE_UPSTREAM:
        try:
            # Disable SSL verification for health check when using upstream proxy
            connector = aiohttp.TCPConnector(ssl=False)
            timeout = ClientTimeout(total=5)
            
            async with ClientSession(connector=connector, timeout=timeout) as session:
                async with session.get('http://httpbin.org/get', proxy=UPSTREAM_PROXY_URL) as response:
                    upstream_status = 'connected' if response.status == 200 else 'error'
        except Exception:
            upstream_status = 'unreachable'
    
    return web.json_response({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'service': 'http-proxy-api-python',
        'port': PORT,
        'upstreamProxy': {
            'enabled': USE_UPSTREAM,
            'url': UPSTREAM_PROXY_URL if USE_UPSTREAM else None,
            'status': upstream_status
        }
    })

async def root_handler(request):
    """Root endpoint"""
    return web.json_response({
        'service': 'HTTP Proxy API (Python)',
        'version': '1.0.0',
        'endpoints': {
            'proxy': '/proxy?url=<encoded_url>',
            'health': '/health'
        },
        'usage': 'Add ?url=<encoded_url> to proxy HTTP content through optional upstream proxy'
    })

async def options_handler(request):
    """Handle OPTIONS requests for CORS"""
    resp = web.Response(status=200)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Headers'] = 'Origin, X-Requested-With, Content-Type, Accept, Range, User-Agent'
    resp.headers['Access-Control-Allow-Methods'] = 'GET, HEAD, OPTIONS'
    resp.headers['Access-Control-Expose-Headers'] = 'Content-Range, Content-Length, Accept-Ranges'
    return resp

async def init_app():
    """Initialize the web application"""
    app = web.Application()
    
    # Add routes (aiohttp automatically creates HEAD routes for GET routes)
    app.router.add_get('/proxy', proxy_handler)
    app.router.add_get('/health', health_handler)
    app.router.add_get('/', root_handler)
    app.router.add_options('/', options_handler)
    app.router.add_options('/proxy', options_handler)
    app.router.add_options('/health', options_handler)
    
    return app

def main():
    """Main entry point"""
    # Test logging first
    log_with_emoji('🚀', "Starting HTTP Proxy API (Python)")
    
    if USE_UPSTREAM:
        log_with_emoji('🔄', f"Using upstream proxy: {UPSTREAM_PROXY_URL}")
        log_with_emoji('🔓', "SSL verification disabled for upstream proxy connections")
    else:
        log_with_emoji('🚫', "Upstream proxy disabled - using direct connections")
        log_with_emoji('🔒', "SSL verification using system truststore")
    
    app = init_app()
    
    log_with_emoji('📡', f"HTTP Proxy API (Python) running on port {PORT}")
    log_with_emoji('🌐', f"Listening on all interfaces (0.0.0.0:{PORT})")
    log_with_emoji('🔗', f"Proxy endpoint: http://localhost:{PORT}/proxy?url=<encoded_url>")
    
    if USE_UPSTREAM:
        log_with_emoji('🔄', f"Routing through upstream proxy: {UPSTREAM_PROXY_URL}")
    else:
        log_with_emoji('🚫', "Direct connections (upstream disabled)")
    
    log_with_emoji('💡', f"Test connectivity: http://localhost:{PORT}/health")
    log_with_emoji('🔧', "Logging system initialized and working")
    
    web.run_app(app, host='0.0.0.0', port=PORT)

if __name__ == '__main__':
    main()