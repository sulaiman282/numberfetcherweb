from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    database_url: str = "sqlite:///./test.db"
    secret_key: str = "your-secret-key-change-in-production"
    admin_username: str = "admin"
    admin_password: str = "admin123"
    external_api_url: str = "https://itbd.online/api/sms/getnum"
    environment: str = "development"
    port: int = 8100
    
    # JWT settings
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours
    

    
    class Config:
        env_file = ".env"

settings = Settings()