"""
DayZ Server API Client
Integrates with Nitrado API for server management

Pattern donor: github.com/DonMatraca/nitrado_api
"""

import os
import asyncio
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from datetime import datetime
import httpx

@dataclass
class ServerInfo:
    """DayZ server information"""
    id: str
    name: str
    game: str
    status: str
    players_current: int
    players_max: int
    ip: str
    port: int
    restart_schedule: Optional[Dict[str, Any]] = None

@dataclass
class PlayerInfo:
    """Player information"""
    name: str
    online: bool
    join_time: Optional[datetime] = None

class NitradoAPIClient:
    """
    Nitrado API client for DayZ server management
    
    Based on dayz-dev-tools and nitrado_api patterns
    """
    
    def __init__(self, api_token: Optional[str] = None):
        self.api_token = api_token or os.getenv("NITRADO_API_TOKEN")
        if not self.api_token:
            raise ValueError("NITRADO_API_TOKEN required")
        
        self.base_url = "https://api.nitrado.net"
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
    
    async def get_servers(self) -> List[ServerInfo]:
        """Get list of all servers"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/services",
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()
            
            servers = []
            for service in data.get("data", {}).get("services", []):
                if service.get("type") == "gameserver":
                    details = service.get("details", {})
                    servers.append(ServerInfo(
                        id=str(service["id"]),
                        name=details.get("name", "Unknown"),
                        game=details.get("game", ""),
                        status=service.get("status", "unknown"),
                        players_current=details.get("slots", {}).get("current", 0),
                        players_max=details.get("slots", {}).get("max", 0),
                        ip=details.get("ip", ""),
                        port=details.get("port", 0)
                    ))
            
            return servers
    
    async def get_server_status(self, server_id: str) -> Dict[str, Any]:
        """Get detailed server status"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/services/{server_id}/gameservers",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json().get("data", {}).get("gameserver", {})
    
    async def restart_server(self, server_id: str, message: Optional[str] = None) -> bool:
        """Restart server with optional message"""
        payload = {}
        if message:
            payload["message"] = message
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/services/{server_id}/gameservers/restart",
                headers=self.headers,
                json=payload
            )
            return response.status_code == 200
    
    async def stop_server(self, server_id: str, message: Optional[str] = None) -> bool:
        """Stop server with optional message"""
        payload = {}
        if message:
            payload["message"] = message
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/services/{server_id}/gameservers/stop",
                headers=self.headers,
                json=payload
            )
            return response.status_code == 200
    
    async def get_players(self, server_id: str) -> List[PlayerInfo]:
        """Get current players on server"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/services/{server_id}/gameservers/players",
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json().get("data", {})
            
            players = []
            for player in data.get("players", []):
                players.append(PlayerInfo(
                    name=player.get("name", ""),
                    online=player.get("online", False),
                    join_time=datetime.fromisoformat(player["join_time"]) if player.get("join_time") else None
                ))
            
            return players
    
    async def send_command(self, server_id: str, command: str) -> Dict[str, Any]:
        """Send RCon command to server"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/services/{server_id}/gameservers/rcon",
                headers=self.headers,
                json={"command": command}
            )
            response.raise_for_status()
            return response.json().get("data", {})
    
    async def get_config_file(self, server_id: str, path: str) -> str:
        """Download configuration file content"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/services/{server_id}/gameservers/file_server/download",
                headers=self.headers,
                params={"file": path}
            )
            response.raise_for_status()
            return response.text
    
    async def upload_config_file(self, server_id: str, path: str, content: str) -> bool:
        """Upload configuration file content"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/services/{server_id}/gameservers/file_server/upload",
                headers=self.headers,
                json={"file": path, "content": content}
            )
            return response.status_code == 200
    
    async def schedule_restart(
        self,
        server_id: str,
        hour: int,
        minute: int,
        message: Optional[str] = None
    ) -> bool:
        """Schedule automatic server restart"""
        payload = {
            "hour": hour,
            "minute": minute
        }
        if message:
            payload["message"] = message
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/services/{server_id}/gameservers/restart_schedule",
                headers=self.headers,
                json=payload
            )
            return response.status_code == 200

# Example usage
if __name__ == "__main__":
    async def main():
        client = NitradoAPIClient()
        
        # Get all servers
        servers = await client.get_servers()
        for server in servers:
            print(f"Server: {server.name} ({server.status})")
            print(f"  Players: {server.players_current}/{server.players_max}")
        
        # Get players on first server
        if servers:
            players = await client.get_players(servers[0].id)
            print(f"\nPlayers on {servers[0].name}:")
            for player in players:
                print(f"  - {player.name} ({'online' if player.online else 'offline'})")
    
    asyncio.run(main())
