from fastapi import Request
import time
import os
from datetime import datetime

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