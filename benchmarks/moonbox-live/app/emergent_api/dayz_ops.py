import os
import asyncio
from typing import Optional, List, Any
from services.dayz_api_client import NitradoAPIClient, ServerInfo

class DayZOps:
    """
    Exhumed Game Server Operations Logic
    Origin: services/dayz_api_client.py
    """
    
    def __init__(self, api_token: Optional[str] = None):
        try:
            self.client = NitradoAPIClient(api_token)
        except ValueError:
            # Fallback for safe instantiation if token missing
            self.client = None
            
    async def list_servers(self) -> List[ServerInfo]:
        if not self.client:
            return []
        return await self.client.get_servers()
        
    async def restart_server(self, server_id: str, message: str = "Restarting for updates...") -> bool:
        if not self.client:
            return False
        return await self.client.restart_server(server_id, message)
