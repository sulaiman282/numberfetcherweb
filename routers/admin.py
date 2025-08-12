from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List
from datetime import timedelta
from database import get_db
from models import AdminUser, NumberRange, Configuration
from schemas import (
    AdminLogin, Token, NumberRange as NumberRangeSchema,
    NumberRangeCreate, NumberRangeUpdate, DashboardResponse
)
from auth import authenticate_user, create_access_token, get_current_user
from services.external_api import ExternalAPIService
from services.range_service import RangeService
from services.timer_service import TimerService

router = APIRouter()

@router.post("/login", response_model=Token)
async def login(
    login_data: AdminLogin,
    db: AsyncSession = Depends(get_db)
):
    """Admin login endpoint"""
    user = await authenticate_user(db, login_data.username, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=1440)  # 24 hours
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get dashboard data"""
    try:
        # Get current configuration
        config_result = await db.execute(
            select(Configuration).where(Configuration.key == "current_config")
        )
        config_row = config_result.scalar_one_or_none()
        config = config_row.value if config_row else {}
        
        # Get balance information
        external_service = ExternalAPIService()
        balance_data = await external_service.get_balance(config)
        
        # Get number ranges
        range_service = RangeService(db)
        ranges = await range_service.get_ranges_by_category()
        
        # Get timer status
        timer_service = TimerService(db)
        timer_status = await timer_service.get_status()
        
        return DashboardResponse(
            status="running",
            balance=balance_data if balance_data.get("success") else {"error": "Failed to fetch balance"},
            ranges=ranges,
            timer_status=timer_status
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ranges", response_model=List[NumberRangeSchema])
async def get_ranges(
    category: str = None,
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get number ranges"""
    query = select(NumberRange)
    if category:
        query = query.where(NumberRange.category == category)
    
    result = await db.execute(query.order_by(NumberRange.updated_at.desc()))
    ranges = result.scalars().all()
    
    return ranges

@router.post("/ranges", response_model=NumberRangeSchema)
async def create_range(
    range_data: NumberRangeCreate,
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create new number range"""
    # Check if range already exists in this category
    existing = await db.execute(
        select(NumberRange).where(
            NumberRange.range_value == range_data.range_value,
            NumberRange.category == range_data.category
        )
    )
    
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Range already exists in this category"
        )
    
    db_range = NumberRange(**range_data.dict())
    db.add(db_range)
    await db.commit()
    await db.refresh(db_range)
    
    return db_range

@router.put("/ranges/{range_id}", response_model=NumberRangeSchema)
async def update_range(
    range_id: int,
    range_data: NumberRangeUpdate,
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update number range"""
    result = await db.execute(
        select(NumberRange).where(NumberRange.id == range_id)
    )
    db_range = result.scalar_one_or_none()
    
    if not db_range:
        raise HTTPException(status_code=404, detail="Range not found")
    
    update_data = range_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_range, field, value)
    
    await db.commit()
    await db.refresh(db_range)
    
    return db_range

@router.delete("/ranges/{range_id}")
async def delete_range(
    range_id: int,
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete number range"""
    result = await db.execute(
        delete(NumberRange).where(NumberRange.id == range_id)
    )
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Range not found")
    
    await db.commit()
    return {"message": "Range deleted successfully"}

@router.get("/balance")
async def get_balance(
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get balance information"""
    try:
        # Get current configuration
        config_result = await db.execute(
            select(Configuration).where(Configuration.key == "current_config")
        )
        config_row = config_result.scalar_one_or_none()
        config = config_row.value if config_row else {}
        
        external_service = ExternalAPIService()
        balance_data = await external_service.get_balance(config)
        
        return balance_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/test-numbers")
async def get_test_numbers(
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get latest test numbers"""
    try:
        # Get current configuration
        config_result = await db.execute(
            select(Configuration).where(Configuration.key == "current_config")
        )
        config_row = config_result.scalar_one_or_none()
        config = config_row.value if config_row else {}
        
        external_service = ExternalAPIService()
        test_data = await external_service.get_access_list(config)
        
        return test_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/timer/start")
async def start_timer(
    category: str,
    interval_minutes: int = 2,
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Start automation timer"""
    timer_service = TimerService(db)
    result = await timer_service.start_timer(category, interval_minutes)
    return result

@router.post("/timer/stop")
async def stop_timer(
    category: str,
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Stop automation timer"""
    timer_service = TimerService(db)
    result = await timer_service.stop_timer(category)
    return result