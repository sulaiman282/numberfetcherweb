#!/usr/bin/env python3
"""
Database initialization script
Creates initial admin user and migrates existing JSON config
"""

import asyncio
import json
import os
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import init_db, AsyncSessionLocal
from models import AdminUser, NumberRange, Configuration, APIProfile
from auth import get_password_hash
from config import settings

async def create_admin_user():
    """Create initial admin user"""
    async with AsyncSessionLocal() as db:
        # Check if admin user already exists
        from sqlalchemy import select
        result = await db.execute(
            select(AdminUser).where(AdminUser.username == settings.admin_username)
        )
        existing_user = result.scalar_one_or_none()
        
        if not existing_user:
            admin_user = AdminUser(
                username=settings.admin_username,
                password_hash=get_password_hash(settings.admin_password),
                is_active=True
            )
            db.add(admin_user)
            await db.commit()
            print(f"Created admin user: {settings.admin_username}")
        else:
            print("Admin user already exists")

async def migrate_json_config():
    """Migrate existing JSON configuration to database"""
    config_file = "../../config.json"
    shared_params_file = "../../shared_params.json"
    
    async with AsyncSessionLocal() as db:
        # Migrate main config
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config_data = json.load(f)
            
            # Save parsed data as current config
            if "parsed_data" in config_data:
                # Check if config already exists
                result = await db.execute(
                    select(Configuration).where(Configuration.key == "current_config")
                )
                existing_config = result.scalar_one_or_none()
                
                if not existing_config:
                    config_obj = Configuration(
                        key="current_config",
                        value=config_data["parsed_data"],
                        updated_by="migration"
                    )
                    db.add(config_obj)
            
            # Migrate favorites
            if "favourites" in config_data:
                for fav in config_data["favourites"]:
                    # Check if range already exists
                    result = await db.execute(
                        select(NumberRange).where(
                            NumberRange.range_value == fav,
                            NumberRange.category == "favorites"
                        )
                    )
                    if not result.scalar_one_or_none():
                        range_obj = NumberRange(
                            range_value=fav,
                            category="favorites",
                            extra_data={
                                "timestamp": config_data.get("favourites_timestamps", {}).get(fav),
                                "migrated": True
                            }
                        )
                        db.add(range_obj)
            
            # Migrate recents
            if "recents" in config_data:
                for recent in config_data["recents"]:
                    # Check if range already exists
                    result = await db.execute(
                        select(NumberRange).where(
                            NumberRange.range_value == recent,
                            NumberRange.category == "recents"
                        )
                    )
                    if not result.scalar_one_or_none():
                        range_obj = NumberRange(
                            range_value=recent,
                            category="recents",
                            extra_data={
                                "timestamp": config_data.get("recents_timestamps", {}).get(recent),
                                "migrated": True
                            }
                        )
                        db.add(range_obj)
            
            # Migrate special
            if "special" in config_data:
                for special in config_data["special"]:
                    # Check if range already exists
                    result = await db.execute(
                        select(NumberRange).where(
                            NumberRange.range_value == special,
                            NumberRange.category == "special"
                        )
                    )
                    if not result.scalar_one_or_none():
                        range_obj = NumberRange(
                            range_value=special,
                            category="special",
                            extra_data={
                                "timestamp": config_data.get("special_timestamps", {}).get(special),
                                "migrated": True
                            }
                        )
                        db.add(range_obj)
            
            # Save pause state
            result = await db.execute(
                select(Configuration).where(Configuration.key == "paused")
            )
            if not result.scalar_one_or_none():
                pause_config = Configuration(
                    key="paused",
                    value={"paused": config_data.get("paused", False)},
                    updated_by="migration"
                )
                db.add(pause_config)
            
            await db.commit()
            print("Migrated config.json data")
        
        # Migrate shared params
        if os.path.exists(shared_params_file):
            with open(shared_params_file, 'r') as f:
                shared_data = json.load(f)
            
            result = await db.execute(
                select(Configuration).where(Configuration.key == "shared_params")
            )
            if not result.scalar_one_or_none():
                shared_config = Configuration(
                    key="shared_params",
                    value=shared_data,
                    updated_by="migration"
                )
                db.add(shared_config)
            await db.commit()
            print("Migrated shared_params.json data")

async def main():
    """Main initialization function"""
    print("Initializing database...")
    
    # Create tables
    await init_db()
    print("Database tables created")
    
    # Create admin user
    await create_admin_user()
    
    # Migrate existing config
    await migrate_json_config()
    
    print("Database initialization complete!")

if __name__ == "__main__":
    asyncio.run(main())