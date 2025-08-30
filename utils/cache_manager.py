import time
import asyncio
import logging
from typing import Dict, Any, Optional, Callable, TypeVar, Union
from collections import OrderedDict
import json
import hashlib
from dataclasses import dataclass
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')

@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    value: Any
    timestamp: float
    ttl: float
    access_count: int = 0
    last_access: float = 0

class CacheManager:
    """Advanced cache manager with TTL, LRU eviction, and memory management"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: Dict[str, CacheEntry] = OrderedDict()
        self.access_times: Dict[str, float] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
    async def start(self):
        """Start the cache manager with background cleanup"""
        if not self._running:
            self._running = True
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Cache manager started")
            
    async def stop(self):
        """Stop the cache manager"""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Cache manager stopped")
        
    async def _cleanup_loop(self):
        """Background task to clean up expired entries"""
        while self._running:
            try:
                await self._cleanup_expired()
                await asyncio.sleep(60)  # Cleanup every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cache cleanup: {e}")
                
    async def _cleanup_expired(self):
        """Remove expired cache entries"""
        async with self._lock:
            current_time = time.time()
            expired_keys = []
            
            for key, entry in self.cache.items():
                if current_time - entry.timestamp > entry.ttl:
                    expired_keys.append(key)
                    
            for key in expired_keys:
                del self.cache[key]
                if key in self.access_times:
                    del self.access_times[key]
                    
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
                
    async def _evict_lru(self):
        """Evict least recently used entries when cache is full"""
        if len(self.cache) >= self.max_size:
            # Find least recently used entry
            lru_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
            del self.cache[lru_key]
            del self.access_times[lru_key]
            logger.debug(f"Evicted LRU cache entry: {lru_key}")
            
    def _make_key(self, *args, **kwargs) -> str:
        """Create a cache key from function arguments"""
        key_data = {
            'args': args,
            'kwargs': sorted(kwargs.items())
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_str.encode()).hexdigest()
        
    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache"""
        async with self._lock:
            if key not in self.cache:
                return None
                
            entry = self.cache[key]
            current_time = time.time()
            
            # Check if expired
            if current_time - entry.timestamp > entry.ttl:
                del self.cache[key]
                if key in self.access_times:
                    del self.access_times[key]
                return None
                
            # Update access metadata
            entry.access_count += 1
            entry.last_access = current_time
            self.access_times[key] = current_time
            
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            
            return entry.value
            
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set a value in cache with optional TTL"""
        async with self._lock:
            # Evict if necessary
            await self._evict_lru()
            
            current_time = time.time()
            expiry = ttl or self.default_ttl
            
            entry = CacheEntry(
                value=value,
                timestamp=current_time,
                ttl=expiry,
                access_count=1,
                last_access=current_time
            )
            
            self.cache[key] = entry
            self.access_times[key] = current_time
            
    async def delete(self, key: str) -> bool:
        """Delete a cache entry"""
        async with self._lock:
            if key in self.cache:
                del self.cache[key]
                if key in self.access_times:
                    del self.access_times[key]
                return True
            return False
            
    async def clear(self) -> None:
        """Clear all cache entries"""
        async with self._lock:
            self.cache.clear()
            self.access_times.clear()
            
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        async with self._lock:
            current_time = time.time()
            total_entries = len(self.cache)
            expired_count = 0
            total_access_count = 0
            
            for entry in self.cache.values():
                if current_time - entry.timestamp > entry.ttl:
                    expired_count += 1
                total_access_count += entry.access_count
                
            return {
                'total_entries': total_entries,
                'expired_entries': expired_count,
                'max_size': self.max_size,
                'utilization': total_entries / self.max_size if self.max_size > 0 else 0,
                'total_access_count': total_access_count,
                'avg_access_count': total_access_count / total_entries if total_entries > 0 else 0
            }

def cached(ttl: Optional[int] = None, key_func: Optional[Callable] = None):
    """Decorator for caching function results"""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        cache_manager = CacheManager()
        
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            # Create cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = cache_manager._make_key(*args, **kwargs)
                
            # Try to get from cache
            cached_result = await cache_manager.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result
                
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache_manager.set(cache_key, result, ttl)
            logger.debug(f"Cache miss for {func.__name__}, cached result")
            
            return result
            
        return wrapper
    return decorator

# Global cache manager instance
cache_manager = CacheManager()

def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance"""
    return cache_manager