"""
LRU Context Cache

Simple LRU (Least Recently Used) cache for BuiltContext.
Thread-safe async operations using asyncio.Lock.
"""
import asyncio
import logging
from collections import OrderedDict
from datetime import datetime, UTC
from typing import Optional

from app.neuroforge.models import BuiltContext

logger = logging.getLogger(__name__)


class LRUContextCache:
    """
    LRU cache for BuiltContext items with TTL support.
    
    Features:
    - Automatic expiration based on TTL
    - Thread-safe async access
    - Configurable max size with automatic eviction of oldest items
    - Metric tracking (hits, misses, evictions)
    """
    
    def __init__(self, max_size: int = 1000):
        """
        Initialize LRU cache.
        
        Args:
            max_size: Maximum number of items to store
        """
        self.max_size = max_size
        self._cache: OrderedDict[str, BuiltContext] = OrderedDict()
        self._lock = asyncio.Lock()
        
        # Metrics
        self.hits = 0
        self.misses = 0
        self.evictions = 0
    
    async def get(self, key: str) -> Optional[BuiltContext]:
        """
        Get item from cache.
        
        Args:
            key: Cache key
        
        Returns:
            BuiltContext if found and not expired, None otherwise
        """
        async with self._lock:
            if key not in self._cache:
                self.misses += 1
                return None
            
            context = self._cache[key]
            
            # Check expiration
            if context.cached_at:
                elapsed = (datetime.now(UTC) - context.cached_at).total_seconds()
                if elapsed > context.ttl_seconds:
                    logger.debug(f"Cache entry expired: {key}")
                    del self._cache[key]
                    self.misses += 1
                    return None
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self.hits += 1
            logger.debug(f"Cache hit: {key}")
            return context
    
    async def put(self, key: str, value: BuiltContext) -> None:
        """
        Put item into cache.
        
        Args:
            key: Cache key
            value: BuiltContext to store
        """
        async with self._lock:
            # Remove old entry if exists
            if key in self._cache:
                del self._cache[key]
            
            # Add new entry
            self._cache[key] = value
            self._cache.move_to_end(key)
            
            # Evict oldest if over limit
            if len(self._cache) > self.max_size:
                oldest_key, _ = self._cache.popitem(last=False)
                self.evictions += 1
                logger.debug(f"Cache evicted oldest entry: {oldest_key}")
            
            logger.debug(f"Cache put: {key} (size={len(self._cache)})")
    
    async def delete(self, key: str) -> bool:
        """
        Delete item from cache.
        
        Args:
            key: Cache key
        
        Returns:
            True if item was present, False otherwise
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Cache delete: {key}")
                return True
            return False
    
    async def clear(self) -> None:
        """Clear entire cache."""
        async with self._lock:
            size = len(self._cache)
            self._cache.clear()
            logger.info(f"Cache cleared ({size} items removed)")
    
    async def size(self) -> int:
        """Get current cache size."""
        async with self._lock:
            return len(self._cache)
    
    async def get_metrics(self) -> dict:
        """
        Get cache metrics.
        
        Returns:
            Dict with hits, misses, hit_rate, evictions, current_size
        """
        async with self._lock:
            total = self.hits + self.misses
            hit_rate = (self.hits / total * 100) if total > 0 else 0.0
            return {
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate_percent": round(hit_rate, 2),
                "evictions": self.evictions,
                "current_size": len(self._cache),
                "max_size": self.max_size,
            }


# Global singleton instance
_context_cache: Optional[LRUContextCache] = None


def get_context_cache() -> LRUContextCache:
    """Get or create the global context cache."""
    global _context_cache
    if _context_cache is None:
        _context_cache = LRUContextCache()
    return _context_cache


def init_context_cache(max_size: int = 1000) -> LRUContextCache:
    """Initialize the global context cache."""
    global _context_cache
    _context_cache = LRUContextCache(max_size=max_size)
    return _context_cache
