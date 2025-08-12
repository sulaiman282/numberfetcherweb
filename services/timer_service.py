from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import Configuration
from typing import Dict, Any
import asyncio
from datetime import datetime, timedelta

class TimerService:
    """Service for managing automation timers"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.active_timers = {}
    
    async def get_status(self) -> Dict[str, Any]:
        """Get current timer status"""
        # Get timer configuration from database
        result = await self.db.execute(
            select(Configuration).where(Configuration.key == "timer_status")
        )
        config = result.scalar_one_or_none()
        
        if config:
            return config.value
        
        return {
            "active": False,
            "current_range": None,
            "next_cycle": None,
            "category": None,
            "interval_minutes": 0
        }
    
    async def start_timer(self, category: str, interval_minutes: int) -> Dict[str, Any]:
        """Start automation timer for a category"""
        try:
            # Stop existing timer if running
            await self.stop_timer(category)
            
            # Update timer status in database
            timer_status = {
                "active": True,
                "category": category,
                "interval_minutes": interval_minutes,
                "started_at": datetime.utcnow().isoformat(),
                "next_cycle": (datetime.utcnow() + timedelta(minutes=interval_minutes)).isoformat()
            }
            
            # Save to database
            result = await self.db.execute(
                select(Configuration).where(Configuration.key == "timer_status")
            )
            config = result.scalar_one_or_none()
            
            if config:
                config.value = timer_status
            else:
                config = Configuration(key="timer_status", value=timer_status)
                self.db.add(config)
            
            await self.db.commit()
            
            return {"success": True, "message": f"Timer started for {category}"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def stop_timer(self, category: str) -> Dict[str, Any]:
        """Stop automation timer for a category"""
        try:
            # Update timer status in database
            timer_status = {
                "active": False,
                "category": None,
                "interval_minutes": 0,
                "stopped_at": datetime.utcnow().isoformat()
            }
            
            # Save to database
            result = await self.db.execute(
                select(Configuration).where(Configuration.key == "timer_status")
            )
            config = result.scalar_one_or_none()
            
            if config:
                config.value = timer_status
            else:
                config = Configuration(key="timer_status", value=timer_status)
                self.db.add(config)
            
            await self.db.commit()
            
            return {"success": True, "message": f"Timer stopped for {category}"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def cycle_ranges(self, category: str):
        """Cycle through ranges in a category"""
        from services.range_service import RangeService
        
        range_service = RangeService(self.db)
        ranges = await range_service.get_category_ranges(category)
        
        if not ranges:
            return None
        
        # Get current index from configuration
        result = await self.db.execute(
            select(Configuration).where(Configuration.key == f"{category}_cycle_index")
        )
        config = result.scalar_one_or_none()
        
        current_index = config.value.get("index", 0) if config else 0
        
        # Get next range
        if current_index >= len(ranges):
            current_index = 0
        
        current_range = ranges[current_index]
        
        # Update current range configuration
        current_config = {
            "current_range": current_range.range_value,
            "category": category,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Save current range
        result = await self.db.execute(
            select(Configuration).where(Configuration.key == "current_range")
        )
        config = result.scalar_one_or_none()
        
        if config:
            config.value = current_config
        else:
            config = Configuration(key="current_range", value=current_config)
            self.db.add(config)
        
        # Update cycle index
        index_config = {
            "index": current_index + 1,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        result = await self.db.execute(
            select(Configuration).where(Configuration.key == f"{category}_cycle_index")
        )
        config = result.scalar_one_or_none()
        
        if config:
            config.value = index_config
        else:
            config = Configuration(key=f"{category}_cycle_index", value=index_config)
            self.db.add(config)
        
        await self.db.commit()
        
        return current_range.range_value