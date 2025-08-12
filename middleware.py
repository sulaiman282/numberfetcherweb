from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
import os
from datetime import datetime
from collections import defaultdict
from typing import Dict
import asyncio

# Rate limiting storage (in production, use Redis)
rate_limit_storage: Dict[str, list] = defaultdict(list)

async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware - disabled for local development"""
    # Skip rate limiting for local development
    environment = os.getenv("ENVIRONMENT", "development")
    if environment == "development":
        response = await call_next(request)
        return response
    
    # Rate limiting for production only
    client_ip = request.client.host
    current_time = time.time()
    
    # Clean old requests (older than 1 hour)
    rate_limit_storage[client_ip] = [
        req_time for req_time in rate_limit_storage[client_ip]
        if current_time - req_time < 3600
    ]
    
    # Check rate limit (100 requests per hour)
    if len(rate_limit_storage[client_ip]) >= 100:
        return Response(
            content='{"error": "Rate limit exceeded"}',
            status_code=429,
            media_type="application/json"
        )
    
    # Add current request
    rate_limit_storage[client_ip].append(current_time)
    
    response = await call_next(request)
    return response

async def logging_middleware(request: Request, call_next):
    """Request logging middleware - simplified for local development"""
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = int((time.time() - start_time) * 1000)
    
    # Only log in development if needed, skip for production noise
    environment = os.getenv("ENVIRONMENT", "development")
    if environment == "development":
        # Minimal logging for development
        if process_time > 1000:  # Only log slow requests
            print(f"{request.method} {request.url.path} - {response.status_code} - {process_time}ms")
    else:
        # Full logging for production
        print(f"{datetime.utcnow().isoformat()} - "
              f"{request.method} {request.url.path} - "
              f"{response.status_code} - {process_time}ms")
    
    return response