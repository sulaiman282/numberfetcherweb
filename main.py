from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import os
from database import init_db
from routers import public, admin
from middleware import rate_limit_middleware, logging_middleware
from config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown
    pass

app = FastAPI(
    title="Number Fetcher API",
    description="Web version of Number Fetcher with admin authentication",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware - more permissive for local development
if settings.environment == "development":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # More restrictive CORS for production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "https://your-frontend-domain.com"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )

# Custom middleware - only add rate limiting in production
if settings.environment == "production":
    app.middleware("http")(rate_limit_middleware)

# Always add logging middleware (but it's simplified for development)
app.middleware("http")(logging_middleware)

# Include routers
app.include_router(public.router, prefix="/api", tags=["public"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])

@app.get("/")
async def root():
    return {"message": "Number Fetcher API v2.0", "status": "running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)