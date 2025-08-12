from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List
from datetime import timedelta
from database import get_db
from models import AdminUser, NumberRange, Configuration, APIProfile
from schemas import (
    AdminLogin, Token, NumberRange as NumberRangeSchema,
    NumberRangeCreate, NumberRangeUpdate, DashboardResponse,
    APIProfile as APIProfileSchema, APIProfileCreate, APIProfileUpdate,
    ProfileLoginResponse
)
from auth import authenticate_user, create_access_token, get_current_user
from services.external_api import ExternalAPIService
from services.range_service import RangeService
from services.timer_service import TimerService
from services.profile_service import ProfileService

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
        # Get balance information using active profile
        external_service = ExternalAPIService(db)
        balance_data = await external_service.get_balance()
        
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
        external_service = ExternalAPIService(db)
        balance_data = await external_service.get_balance()
        
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
        external_service = ExternalAPIService(db)
        test_data = await external_service.get_access_list()
        
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

# Profile Management Endpoints

@router.get("/profiles", response_model=List[APIProfileSchema])
async def get_profiles(
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all API profiles"""
    profile_service = ProfileService(db)
    profiles = await profile_service.get_all_profiles()
    return profiles

@router.post("/profiles", response_model=APIProfileSchema)
async def create_profile(
    profile_data: APIProfileCreate,
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create new API profile"""
    profile_service = ProfileService(db)
    profile = await profile_service.create_profile(
        name=profile_data.name,
        auth_token=profile_data.auth_token
    )
    return profile

@router.put("/profiles/{profile_id}", response_model=APIProfileSchema)
async def update_profile(
    profile_id: int,
    profile_data: APIProfileUpdate,
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update API profile"""
    result = await db.execute(
        select(APIProfile).where(APIProfile.id == profile_id)
    )
    profile = result.scalar_one_or_none()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    update_data = profile_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)
    
    await db.commit()
    await db.refresh(profile)
    
    return profile

@router.delete("/profiles/{profile_id}")
async def delete_profile(
    profile_id: int,
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete API profile"""
    profile_service = ProfileService(db)
    success = await profile_service.delete_profile(profile_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return {"message": "Profile deleted successfully"}

@router.post("/profiles/{profile_id}/activate")
async def activate_profile(
    profile_id: int,
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Activate a specific profile"""
    profile_service = ProfileService(db)
    success = await profile_service.activate_profile(profile_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return {"message": "Profile activated successfully"}

@router.post("/profiles/{profile_id}/login", response_model=ProfileLoginResponse)
async def login_profile(
    profile_id: int,
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Attempt to login with a profile's auth token"""
    profile_service = ProfileService(db)
    result = await profile_service.login_profile(profile_id)
    return result

@router.get("/profiles/active", response_model=APIProfileSchema)
async def get_active_profile(
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get the currently active profile"""
    profile_service = ProfileService(db)
    profile = await profile_service.get_active_profile()
    
    if not profile:
        raise HTTPException(status_code=404, detail="No active profile found")
    
    return profile