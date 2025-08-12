import httpx
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import APIProfile
from typing import Dict, Any, Optional

class ProfileService:
    """Service for managing API profiles and external login"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.login_url = "https://itbd.online/api/login"
        self.timeout = 10
    
    async def create_profile(self, name: str, auth_token: str) -> tuple[APIProfile, dict]:
        """Create a new API profile and auto-login"""
        # Deactivate all other profiles first
        await self.deactivate_all_profiles()
        
        profile = APIProfile(
            name=name,
            auth_token=auth_token,
            is_active=True,  # New profile becomes active by default
            is_logged_in=False,
            login_status="not_attempted"
        )
        
        self.db.add(profile)
        await self.db.commit()
        await self.db.refresh(profile)
        
        # Auto-login the new profile
        login_result = await self.login_profile(profile.id)
        
        return profile, login_result
    
    async def get_all_profiles(self) -> list[APIProfile]:
        """Get all API profiles"""
        result = await self.db.execute(select(APIProfile).order_by(APIProfile.created_at.desc()))
        return result.scalars().all()
    
    async def get_active_profile(self) -> Optional[APIProfile]:
        """Get the currently active profile"""
        result = await self.db.execute(
            select(APIProfile).where(APIProfile.is_active == True)
        )
        return result.scalar_one_or_none()
    
    async def activate_profile(self, profile_id: int) -> bool:
        """Activate a specific profile and deactivate others"""
        # Deactivate all profiles
        await self.deactivate_all_profiles()
        
        # Activate the selected profile
        result = await self.db.execute(
            select(APIProfile).where(APIProfile.id == profile_id)
        )
        profile = result.scalar_one_or_none()
        
        if profile:
            profile.is_active = True
            await self.db.commit()
            return True
        
        return False
    
    async def deactivate_all_profiles(self):
        """Deactivate all profiles"""
        result = await self.db.execute(select(APIProfile))
        profiles = result.scalars().all()
        
        for profile in profiles:
            profile.is_active = False
        
        await self.db.commit()
    
    async def login_profile(self, profile_id: int) -> Dict[str, Any]:
        """Attempt to login with a profile's auth token using the exact curl request format"""
        result = await self.db.execute(
            select(APIProfile).where(APIProfile.id == profile_id)
        )
        profile = result.scalar_one_or_none()
        
        if not profile:
            return {"success": False, "message": "Profile not found"}
        
        try:
            # Prepare the exact headers from the curl request
            headers = {
                "accept": "*/*",
                "accept-language": "en-US,en;q=0.9",
                "content-type": "application/json",
                "origin": "https://itbd.online",
                "priority": "u=1, i",
                "referer": "https://itbd.online/",
                "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
            }
            
            # Cookies from the curl request
            cookies = {
                "_ga": "GA1.1.290468168.1753911312",
                "_ga_9MJB2R4JD4": "GS2.1.s1754563840$o6$g0$t1754563941$j60$l0$h0",
                "TawkConnectionTime": "0",
                "twk_uuid_681787a55d55ef191a9da720": "%7B%22uuid%22%3A%221.70ieXQVh4lUvtU0xKYLUgsDABulwZhw3ztAUWycySPjriKZuE0iWvi3VihlonIbI1PyZEo1wgeOIN8VzLHmHGsWb6Hbas35gAsLzJtc9sLJhnC2CCF0W%22%2C%22version%22%3A3%2C%22domain%22%3A%22itbd.online%22%2C%22ts%22%3A1755028641783%7D"
            }
            
            # Data payload with the auth token
            data = {"authToken": profile.auth_token}
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.login_url,
                    headers=headers,
                    cookies=cookies,
                    json=data
                )
                
                # Update profile with login attempt
                profile.last_login_attempt = datetime.utcnow()
                
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        
                        if response_data.get("code") == 200 and response_data.get("message") == "Login successful":
                            # Successful login - save all the response data
                            data_section = response_data.get("data", {})
                            
                            profile.is_logged_in = True
                            profile.login_status = "success"
                            profile.username = data_section.get("username")
                            profile.email = data_section.get("email")
                            
                            # Store the session token from the response (this is what we use for API calls)
                            profile.session_token = data_section.get("authToken", profile.auth_token)
                            
                            # Parse session expires if available
                            session_expires_str = data_section.get("sessionExpires")
                            if session_expires_str:
                                try:
                                    profile.session_expires = datetime.strptime(
                                        session_expires_str, "%Y-%m-%d %H:%M:%S"
                                    )
                                except ValueError:
                                    # Try alternative format if needed
                                    try:
                                        profile.session_expires = datetime.fromisoformat(
                                            session_expires_str.replace(" ", "T")
                                        )
                                    except ValueError:
                                        pass
                            
                            await self.db.commit()
                            
                            return {
                                "success": True,
                                "message": "Login successful",
                                "profile_data": {
                                    "username": profile.username,
                                    "email": profile.email,
                                    "session_expires": session_expires_str,
                                    "full_response": response_data  # Save full response for debugging
                                }
                            }
                        else:
                            # Login failed based on response
                            profile.is_logged_in = False
                            profile.login_status = "failed"
                            await self.db.commit()
                            
                            return {
                                "success": False,
                                "message": response_data.get("message", "Login failed"),
                                "response_data": response_data
                            }
                    except Exception as json_error:
                        # JSON parsing error
                        profile.is_logged_in = False
                        profile.login_status = "failed"
                        await self.db.commit()
                        
                        return {
                            "success": False,
                            "message": f"Invalid JSON response: {str(json_error)}",
                            "raw_response": response.text
                        }
                else:
                    # HTTP error
                    profile.is_logged_in = False
                    profile.login_status = "failed"
                    await self.db.commit()
                    
                    return {
                        "success": False,
                        "message": f"HTTP Error {response.status_code}",
                        "response_text": response.text
                    }
                    
        except Exception as e:
            # Exception occurred
            profile.is_logged_in = False
            profile.login_status = "failed"
            await self.db.commit()
            
            return {
                "success": False,
                "message": f"Login error: {str(e)}"
            }
    
    async def delete_profile(self, profile_id: int) -> bool:
        """Delete a profile"""
        result = await self.db.execute(
            select(APIProfile).where(APIProfile.id == profile_id)
        )
        profile = result.scalar_one_or_none()
        
        if profile:
            await self.db.delete(profile)
            await self.db.commit()
            return True
        
        return False
    
    async def get_active_profile_config(self) -> Optional[Dict[str, Any]]:
        """Get the configuration for the active profile for API calls"""
        active_profile = await self.get_active_profile()
        
        if not active_profile or not active_profile.is_logged_in:
            return None
        
        # Return the configuration that can be used for external API calls
        return {
            "auth_token": active_profile.auth_token,  # Original token for login
            "session_token": active_profile.session_token or active_profile.auth_token,  # Session token for API calls
            "username": active_profile.username,
            "email": active_profile.email,
            "session_expires": active_profile.session_expires,
            "headers": {
                "accept": "*/*",
                "accept-language": "en-US,en;q=0.9",
                "content-type": "application/json",
                "origin": "https://itbd.online",
                "priority": "u=1, i",
                "referer": "https://itbd.online/user_report_1",
                "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "sessionauth": "null",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
                "x-requested-with": "XMLHttpRequest"
            }
        }