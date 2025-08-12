from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import NumberRange
from typing import Dict, List

class RangeService:
    """Service for managing number ranges"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_ranges_by_category(self) -> Dict[str, List[str]]:
        """Get all ranges grouped by category"""
        result = await self.db.execute(
            select(NumberRange).order_by(NumberRange.updated_at.desc())
        )
        ranges = result.scalars().all()
        
        grouped = {
            "favorites": [],
            "recents": [],
            "special": []
        }
        
        for range_obj in ranges:
            if range_obj.category in grouped:
                grouped[range_obj.category].append(range_obj.range_value)
        
        return grouped
    
    async def add_to_category(self, range_value: str, category: str, extra_data: dict = None):
        """Add range to specific category"""
        # Check if already exists
        existing = await self.db.execute(
            select(NumberRange).where(
                NumberRange.range_value == range_value,
                NumberRange.category == category
            )
        )
        
        if existing.scalar_one_or_none():
            return False  # Already exists
        
        # Remove from other categories if exists
        await self.db.execute(
            select(NumberRange).where(NumberRange.range_value == range_value)
        )
        
        # Add to new category
        new_range = NumberRange(
            range_value=range_value,
            category=category,
            extra_data=extra_data or {}
        )
        
        self.db.add(new_range)
        await self.db.commit()
        
        return True
    
    async def remove_from_category(self, range_value: str, category: str):
        """Remove range from specific category"""
        result = await self.db.execute(
            select(NumberRange).where(
                NumberRange.range_value == range_value,
                NumberRange.category == category
            )
        )
        
        range_obj = result.scalar_one_or_none()
        if range_obj:
            await self.db.delete(range_obj)
            await self.db.commit()
            return True
        
        return False
    
    async def get_category_ranges(self, category: str) -> List[NumberRange]:
        """Get all ranges for a specific category"""
        result = await self.db.execute(
            select(NumberRange)
            .where(NumberRange.category == category)
            .order_by(NumberRange.updated_at.desc())
        )
        
        return result.scalars().all()