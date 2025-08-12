import httpx
from typing import Dict, Any, Optional
from config import settings
from services.profile_service import ProfileService
from sqlalchemy.ext.asyncio import AsyncSession

class ExternalAPIService:
    """Service for handling external API calls"""
    
    def __init__(self, db: Optional[AsyncSession] = None):
        self.timeout = 10
        self.db = db
    
    async def get_active_config(self) -> Optional[Dict[str, Any]]:
        """Get configuration from active profile or fallback to default"""
        if self.db:
            profile_service = ProfileService(self.db)
            profile_config = await profile_service.get_active_profile_config()
            
            if profile_config:
                return {
                    "url": "https://itbd.online/api/sms/getnum",
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
                    },
                    "cookies": {
                        "_ga": "GA1.1.290468168.1753911312",
                        "_ga_9MJB2R4JD4": "GS2.1.s1754563840$o6$g0$t1754563941$j60$l0$h0",
                        "TawkConnectionTime": "0",
                        "twk_uuid_681787a55d55ef191a9da720": "%7B%22uuid%22%3A%221.70ieXQVh4lUvtU0xKYLUgsDABulwZhw3ztAUWycySPjriKZuE0iWvi3VihlonIbI1PyZEo1wgeOIN8VzLHmHGsWb6Hbas35gAsLzJtc9sLJhnC2CCF0W%22%2C%22version%22%3A3%2C%22domain%22%3A%22itbd.online%22%2C%22ts%22%3A1755028641783%7D"
                    },
                    "auth_token": profile_config["auth_token"]
                }
        
        # Fallback to default configuration (no auth token)
        return {
            "url": "https://itbd.online/api/sms/getnum",
            "headers": {
                "accept": "*/*",
                "accept-language": "en-US,en;q=0.5",
                "content-type": "application/json",
                "origin": "https://itbd.online",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
            "cookies": {}
        }

    async def fetch_number(self, number_range: str = None) -> httpx.Response:
        """Make external API call to fetch number using active profile's auth token"""
        config = await self.get_active_config()
        
        data = {
            "app": "null",
            "carrier": "null", 
            "numberRange": number_range or "24996218XXXX",
            "national": False,
            "removePlus": False
        }
        
        # Add auth token if available from active profile
        if "auth_token" in config:
            data["authToken"] = config["auth_token"]
        
        # Update referer with the number range
        headers = config["headers"].copy()
        if number_range:
            headers["referer"] = f"https://itbd.online/user_report_1?getfrange={number_range}"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                config["url"],
                headers=headers,
                cookies=config.get("cookies", {}),
                json=data
            )
            return response
    
    async def get_access_list(self) -> Dict[str, Any]:
        """Get latest test numbers from source-idea endpoint"""
        try:
            config = await self.get_active_config()
            url = "https://itbd.online/api/source-idea?action=get_access_list"
            
            headers = config["headers"].copy()
            headers.update({
                "accept": "application/json, text/javascript, */*; q=0.01",
                "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
                "referer": "https://itbd.online/source-idea",
                "x-requested-with": "XMLHttpRequest"
            })
            
            data = "prefix=&source=&keyword=chatgpt"
            
            # Add auth token if available from active profile
            if "auth_token" in config:
                data += f"&authToken={config['auth_token']}"
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    cookies=config.get("cookies", {}),
                    data=data
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    if response_data.get("success") and "results" in response_data:
                        results = response_data["results"]
                        
                        # Sort by datetime (newest first)
                        try:
                            from datetime import datetime as dt
                            results.sort(
                                key=lambda x: dt.strptime(
                                    x.get("Datetime", "1900-01-01 00:00:00"), 
                                    "%Y-%m-%d %H:%M:%S"
                                ), 
                                reverse=True
                            )
                        except Exception:
                            pass
                        
                        # Filter working numbers
                        working_numbers = []
                        for result in results:
                            test_number = result.get("Test number", "").strip()
                            if test_number:
                                working_numbers.append({
                                    "test_number": test_number,
                                    "comment": result.get("Comment", ""),
                                    "datetime": result.get("Datetime", ""),
                                    "rate": result.get("Rate", ""),
                                    "currency": result.get("Currency", "")
                                })
                        
                        # Take only the latest 10
                        working_numbers = working_numbers[:10]
                        
                        return {
                            "success": True,
                            "working_numbers": working_numbers,
                            "total_results": len(response_data["results"])
                        }
                    else:
                        return {"success": False, "error": "Invalid response format"}
                else:
                    return {"success": False, "error": f"HTTP {response.status_code}"}
                    
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_balance(self) -> Dict[str, Any]:
        """Get balance information from user summary endpoint"""
        try:
            config = await self.get_active_config()
            url = "https://itbd.online/api/user/summary/29"
            
            headers = config["headers"].copy()
            headers.update({
                "referer": "https://itbd.online/summary",
                "userrate": "0.007"
            })
            
            # Add auth token if available from active profile
            if "auth_token" in config:
                # For balance API, we might need to add the token differently
                # Let's try adding it as a parameter or header based on the API requirements
                headers["authToken"] = config["auth_token"]
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    url,
                    headers=headers,
                    cookies=config.get("cookies", {})
                )
                
                if response.status_code == 200:
                    balance_data = response.json()
                    if isinstance(balance_data, list) and len(balance_data) > 0:
                        today_data = balance_data[0]
                        total_balance = sum(item.get("amount", 0) for item in balance_data)
                        
                        return {
                            "success": True,
                            "today_balance": today_data.get("amount", 0),
                            "today_otp": today_data.get("otp", 0),
                            "today_date": today_data.get("date", ""),
                            "total_balance": round(total_balance, 3)
                        }
                    else:
                        return {"success": False, "error": "No balance data available"}
                else:
                    return {"success": False, "error": f"HTTP {response.status_code}"}
                    
        except Exception as e:
            return {"success": False, "error": str(e)}