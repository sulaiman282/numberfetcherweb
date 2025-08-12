from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData
from config import settings
import asyncio

# Database engine
if settings.database_url.startswith("sqlite"):
    # For SQLite, use aiosqlite
    database_url = settings.database_url.replace("sqlite:///", "sqlite+aiosqlite:///")
elif settings.database_url.startswith("postgresql://"):
    # For PostgreSQL, use asyncpg
    database_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
else:
    database_url = settings.database_url

engine = create_async_engine(
    database_url,
    echo=settings.environment == "development"
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

class Base(DeclarativeBase):
    metadata = MetaData()

async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    """Dependency to get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()