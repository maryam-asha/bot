import time
import logging
import asyncio
from functools import wraps
from typing import Dict, List, Optional, Callable, Any
from collections import defaultdict
import tracemalloc
from contextlib import asynccontextmanager, contextmanager

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """Performance monitoring utility for tracking execution times and memory usage"""
    
    def __init__(self):
        self.execution_times: Dict[str, List[float]] = defaultdict(list)
        self.memory_usage: Dict[str, List[float]] = defaultdict(list)
        self.call_counts: Dict[str, int] = defaultdict(int)
        self.active_timers: Dict[str, float] = {}
        self.tracemalloc_enabled = False
        
    def enable_tracemalloc(self):
        """Enable memory tracking"""
        tracemalloc.start()
        self.tracemalloc_enabled = True
        
    def disable_tracemalloc(self):
        """Disable memory tracking"""
        if self.tracemalloc_enabled:
            tracemalloc.stop()
            self.tracemalloc_enabled = False
            
    @contextmanager
    def timer(self, name: str):
        """Context manager for timing execution"""
        start_time = time.time()
        self.active_timers[name] = start_time
        try:
            yield
        finally:
            if name in self.active_timers:
                execution_time = time.time() - self.active_timers[name]
                self.execution_times[name].append(execution_time)
                self.call_counts[name] += 1
                del self.active_timers[name]
                
    @asynccontextmanager
    async def async_timer(self, name: str):
        """Async context manager for timing execution"""
        start_time = time.time()
        self.active_timers[name] = start_time
        try:
            yield
        finally:
            if name in self.active_timers:
                execution_time = time.time() - self.active_timers[name]
                self.execution_times[name].append(execution_time)
                self.call_counts[name] += 1
                del self.active_timers[name]
                
    def time_function(self, func: Callable) -> Callable:
        """Decorator for timing synchronous functions"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            with self.timer(func.__name__):
                return func(*args, **kwargs)
        return wrapper
        
    def time_async_function(self, func: Callable) -> Callable:
        """Decorator for timing asynchronous functions"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            async with self.async_timer(func.__name__):
                return await func(*args, **kwargs)
        return wrapper
        
    def get_statistics(self, name: str) -> Dict[str, Any]:
        """Get performance statistics for a specific function/operation"""
        times = self.execution_times[name]
        if not times:
            return {
                'name': name,
                'call_count': 0,
                'avg_time': 0,
                'min_time': 0,
                'max_time': 0,
                'total_time': 0
            }
            
        return {
            'name': name,
            'call_count': self.call_counts[name],
            'avg_time': sum(times) / len(times),
            'min_time': min(times),
            'max_time': max(times),
            'total_time': sum(times)
        }
        
    def get_slowest_functions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the slowest functions based on average execution time"""
        stats = [self.get_statistics(name) for name in self.execution_times.keys()]
        return sorted(stats, key=lambda x: x['avg_time'], reverse=True)[:limit]
        
    def get_most_called_functions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the most called functions"""
        stats = [self.get_statistics(name) for name in self.execution_times.keys()]
        return sorted(stats, key=lambda x: x['call_count'], reverse=True)[:limit]
        
    def print_summary(self):
        """Print a summary of performance statistics"""
        logger.info("=== Performance Summary ===")
        
        slowest = self.get_slowest_functions(5)
        most_called = self.get_most_called_functions(5)
        
        logger.info("Slowest functions:")
        for stat in slowest:
            logger.info(f"  {stat['name']}: {stat['avg_time']:.4f}s avg ({stat['call_count']} calls)")
            
        logger.info("Most called functions:")
        for stat in most_called:
            logger.info(f"  {stat['name']}: {stat['call_count']} calls ({stat['avg_time']:.4f}s avg)")
            
    def reset(self):
        """Reset all performance data"""
        self.execution_times.clear()
        self.memory_usage.clear()
        self.call_counts.clear()
        self.active_timers.clear()

# Global performance monitor instance
performance_monitor = PerformanceMonitor()

def monitor_performance(func: Callable) -> Callable:
    """Decorator for monitoring function performance"""
    return performance_monitor.time_function(func)

def monitor_async_performance(func: Callable) -> Callable:
    """Decorator for monitoring async function performance"""
    return performance_monitor.time_async_function(func)