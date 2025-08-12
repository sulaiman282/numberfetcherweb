#!/usr/bin/env python3
"""
Startup script for the Number Fetcher backend
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

async def main():
    """Main startup function"""
    print("🚀 Starting Number Fetcher Backend...")
    
    # Initialize database
    print("📊 Initializing database...")
    from init_db import main as init_db_main
    await init_db_main()
    
    # Start the server
    print("🌐 Starting FastAPI server...")
    import uvicorn
    
    # Get port from settings
    from config import settings
    port = settings.port
    host = os.getenv("HOST", "0.0.0.0")
    
    # Run the server
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=os.getenv("ENVIRONMENT", "development") == "development",
        log_level="info"
    )

if __name__ == "__main__":
    asyncio.run(main())