import httpx
import asyncio
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager
import logging

logger = logging.getLogger(__name__)

class HTTPClient:
    """HTTP client with connection pooling and session management"""
    
    def __init__(
        self, 
        base_url: str, 
        timeout: int = 30,
        max_connections: int = 100,
        max_keepalive_connections: int = 20
    ):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_connections = max_connections
        self.max_keepalive_connections = max_keepalive_connections
        self._client: Optional[httpx.AsyncClient] = None
        self._session_lock = asyncio.Lock()
    
    @asynccontextmanager
    async def get_client(self):
        """Get HTTP client with proper session management"""
        async with self._session_lock:
            if self._client is None:
                self._client = httpx.AsyncClient(
                    base_url=self.base_url,
                    timeout=self.timeout,
                    limits=httpx.Limits(
                        max_connections=self.max_connections,
                        max_keepalive_connections=self.max_keepalive_connections
                    ),
                    http2=True
                )
            
            try:
                yield self._client
            except Exception as e:
                logger.error(f"HTTP client error: {str(e)}")
                # Close client on error to force recreation
                await self.close()
                raise
    
    async def get(
        self, 
        endpoint: str, 
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> httpx.Response:
        """Make GET request"""
        async with self.get_client() as client:
            response = await client.get(endpoint, headers=headers, params=params)
            response.raise_for_status()
            return response
    
    async def post(
        self, 
        endpoint: str, 
        headers: Optional[Dict[str, str]] = None,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None
    ) -> httpx.Response:
        """Make POST request"""
        async with self.get_client() as client:
            response = await client.post(
                endpoint, 
                headers=headers, 
                json=json, 
                data=data, 
                files=files
            )
            response.raise_for_status()
            return response
    
    async def put(
        self, 
        endpoint: str, 
        headers: Optional[Dict[str, str]] = None,
        json: Optional[Dict[str, Any]] = None
    ) -> httpx.Response:
        """Make PUT request"""
        async with self.get_client() as client:
            response = await client.put(endpoint, headers=headers, json=json)
            response.raise_for_status()
            return response
    
    async def delete(
        self, 
        endpoint: str, 
        headers: Optional[Dict[str, str]] = None
    ) -> httpx.Response:
        """Make DELETE request"""
        async with self.get_client() as client:
            response = await client.delete(endpoint, headers=headers)
            response.raise_for_status()
            return response
    
    async def close(self) -> None:
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
