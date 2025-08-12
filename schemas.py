from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# Auth schemas
class AdminLogin(BaseModel):
    username: str
    password: str

class AdminUser(BaseModel):
    id: int
    username: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

# Number Range schemas
class NumberRangeCreate(BaseModel):
    range_value: str = Field(..., min_length=1, max_length=20)
    category: str = Field(..., pattern="^(favorites|recents|special)$")
    extra_data: Optional[Dict[str, Any]] = None

class NumberRangeUpdate(BaseModel):
    range_value: Optional[str] = Field(None, min_length=1, max_length=20)
    category: Optional[str] = Field(None, pattern="^(favorites|recents|special)$")
    extra_data: Optional[Dict[str, Any]] = None

class NumberRange(BaseModel):
    id: int
    range_value: str
    category: str
    created_at: datetime
    updated_at: datetime
    extra_data: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True

# API Response schemas
class FetchNumberResponse(BaseModel):
    success: bool
    number: Optional[str] = None
    sid: Optional[str] = None
    message: str
    error: Optional[str] = None

class DashboardResponse(BaseModel):
    status: str
    balance: Dict[str, Any]
    ranges: Dict[str, List[str]]
    timer_status: Dict[str, Any]

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    database: str

# Profile schemas
class APIProfileCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    auth_token: str = Field(..., min_length=10, max_length=500)

class APIProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    auth_token: Optional[str] = Field(None, min_length=10, max_length=500)

class APIProfile(BaseModel):
    id: int
    name: str
    auth_token: str
    session_token: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    session_expires: Optional[datetime] = None
    is_active: bool
    is_logged_in: bool
    created_at: datetime
    updated_at: datetime
    last_login_attempt: Optional[datetime] = None
    login_status: str
    
    class Config:
        from_attributes = True

class ProfileLoginResponse(BaseModel):
    success: bool
    message: str
    profile_data: Optional[Dict[str, Any]] = None