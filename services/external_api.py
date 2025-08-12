import httpx
from typing import Dict, Any
from config import settings

class ExternalAPIService:
    """Service for handling external API calls"""
    
    def __init__(self):
        self.timeout = 10
    
    async def fetch_number(self, config: Dict[str, Any]) -> httpx.Response:
        """Make external API call to fetch number"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                config["url"],
                headers=config["headers"],
                cookies=config.get("cookies", {}),
                json=config["data"]
            )
            return response
    
    async def get_access_list(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Get latest test numbers from source-idea endpoint"""
        try:
            url = "https://itbd.online/api/source-idea?action=get_access_list"
            
            headers = config["headers"].copy()
            headers.update({
                "accept": "application/json, text/javascript, */*; q=0.01",
                "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
                "referer": "https://itbd.online/source-idea",
                "x-requested-with": "XMLHttpRequest"
            })
            
            data = "prefix=&source=&keyword=chatgpt"
            
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
    
    async def get_balance(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Get balance information from user summary endpoint"""
        try:
            url = "https://itbd.online/api/user/summary/29"
            
            headers = config["headers"].copy()
            headers.update({
                "referer": "https://itbd.online/summary",
                "userrate": "0.007"
            })
            
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