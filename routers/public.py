from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx
import json
from datetime import datetime
from database import get_db
from models import Configuration
from schemas import FetchNumberResponse, HealthResponse
from services.external_api import ExternalAPIService

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check endpoint"""
    try:
        # Test database connection
        await db.execute(select(1))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    
    return HealthResponse(
        status="running",
        timestamp=datetime.utcnow(),
        database=db_status
    )

@router.get("/fetch-number")
async def fetch_number(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Fetch number with default configuration"""
    try:
        # Get current configuration from database
        config_result = await db.execute(
            select(Configuration).where(Configuration.key == "current_config")
        )
        config_row = config_result.scalar_one_or_none()
        
        if not config_row:
            # Use default configuration
            default_config = {
                "url": "https://itbd.online/api/sms/getnum",
                "headers": {
                    "accept": "*/*",
                    "accept-language": "en-US,en;q=0.5",
                    "content-type": "application/json",
                    "origin": "https://itbd.online",
                    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
                "cookies": {},
                "data": {
                    "app": "null",
                    "carrier": "null",
                    "numberRange": "24996218XXXX",
                    "national": False,
                    "removePlus": False
                }
            }
        else:
            default_config = config_row.value
        
        # Check if paused
        pause_result = await db.execute(
            select(Configuration).where(Configuration.key == "paused")
        )
        pause_row = pause_result.scalar_one_or_none()
        
        if pause_row and pause_row.value.get("paused", False):
            return {"error": "Server is paused"}
        
        # Make external API call
        external_service = ExternalAPIService(db)
        response = await external_service.fetch_number()
        
        return Response(
            content=response.content,
            status_code=response.status_code,
            media_type=response.headers.get("content-type", "application/json")
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/fetch-number/range/{number_range}")
async def fetch_number_with_range(
    number_range: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Fetch number with specific range"""
    try:
        # Get current configuration from database
        config_result = await db.execute(
            select(Configuration).where(Configuration.key == "current_config")
        )
        config_row = config_result.scalar_one_or_none()
        
        if not config_row:
            # Use default configuration
            config = {
                "url": "https://itbd.online/api/sms/getnum",
                "headers": {
                    "accept": "*/*",
                    "accept-language": "en-US,en;q=0.5",
                    "content-type": "application/json",
                    "origin": "https://itbd.online",
                    "referer": f"https://itbd.online/user_report_1?getfrange={number_range}",
                    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
                "cookies": {},
                "data": {
                    "app": "null",
                    "carrier": "null",
                    "numberRange": number_range,
                    "national": False,
                    "removePlus": False
                }
            }
        else:
            config = config_row.value.copy()
            config["data"]["numberRange"] = number_range
            config["headers"]["referer"] = f"https://itbd.online/user_report_1?getfrange={number_range}"
        
        # Make external API call
        external_service = ExternalAPIService(db)
        response = await external_service.fetch_number(number_range)
        
        return Response(
            content=response.content,
            status_code=response.status_code,
            media_type=response.headers.get("content-type", "application/json")
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))