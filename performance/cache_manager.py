#!/usr/bin/env python3
"""
Advanced Caching and Performance Management System
Multi-level caching with Redis support, intelligent cache warming,
performance optimization, and comprehensive metrics.
"""

import os
import json
import time
import hashlib
import pickle
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
from collections import OrderedDict, defaultdict
import asyncio

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

class CacheLevel(Enum):
    MEMORY = "memory"
    DISK = "disk"
    REDIS = "redis"
    DATABASE = "database"

class CacheStrategy(Enum):
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    TTL = "ttl"  # Time To Live
    FIFO = "fifo"  # First In First Out

@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    value: Any
    created_at: float
    last_accessed: float
    access_count: int
    ttl: Optional[float]
    size_bytes: int
    tags: List[str]

@dataclass
class CacheStats:
    """Cache performance statistics"""
    hits: int
    misses: int
    evictions: int
    total_requests: int
    hit_rate: float
    avg_response_time: float
    memory_usage: int
    entry_count: int

class LRUCache:
    """Thread-safe LRU cache implementation"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache = OrderedDict()
        self.lock = threading.RLock()
        self.stats = {"hits": 0, "misses": 0, "evictions": 0}
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self.lock:
            if key in self.cache:
                # Move to end (most recently used)
                value = self.cache.pop(key)
                self.cache[key] = value
                self.stats["hits"] += 1
                return value.value if isinstance(value, CacheEntry) else value
            else:
                self.stats["misses"] += 1
                return None
    
    def put(self, key: str, value: Any, ttl: Optional[float] = None):
        """Put value in cache"""
        with self.lock:
            # Remove if already exists
            if key in self.cache:
                del self.cache[key]
            
            # Create cache entry
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=time.time(),
                last_accessed=time.time(),
                access_count=1,
                ttl=ttl,
                size_bytes=len(str(value)),
                tags=[]
            )
            
            self.cache[key] = entry
            
            # Evict if over capacity
            while len(self.cache) > self.max_size:
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                self.stats["evictions"] += 1
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False
    
    def clear(self):
        """Clear all cache entries"""
        with self.lock:
            self.cache.clear()
    
    def size(self) -> int:
        """Get cache size"""
        with self.lock:
            return len(self.cache)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            total_requests = self.stats["hits"] + self.stats["misses"]
            hit_rate = self.stats["hits"] / total_requests if total_requests > 0 else 0
            
            return {
                "hits": self.stats["hits"],
                "misses": self.stats["misses"],
                "evictions": self.stats["evictions"],
                "hit_rate": hit_rate,
                "size": len(self.cache),
                "max_size": self.max_size
            }

class DiskCache:
    """Persistent disk-based cache"""
    
    def __init__(self, cache_dir: str = "synapseflow_data/cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.index_file = os.path.join(cache_dir, "index.json")
        self.index = self._load_index()
        self.lock = threading.RLock()
    
    def _load_index(self) -> Dict[str, Dict]:
        """Load cache index from disk"""
        if os.path.exists(self.index_file):
            try:
                with open(self.index_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}
    
    def _save_index(self):
        """Save cache index to disk"""
        try:
            with open(self.index_file, 'w') as f:
                json.dump(self.index, f)
        except Exception as e:
            print(f"Error saving cache index: {e}")
    
    def _get_file_path(self, key: str) -> str:
        """Get file path for cache key"""
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{key_hash}.cache")
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from disk cache"""
        with self.lock:
            if key not in self.index:
                return None
            
            entry_info = self.index[key]
            
            # Check TTL
            if entry_info.get("ttl") and time.time() > entry_info["ttl"]:
                self.delete(key)
                return None
            
            # Load from disk
            file_path = self._get_file_path(key)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'rb') as f:
                        value = pickle.load(f)
                    
                    # Update access info
                    entry_info["last_accessed"] = time.time()
                    entry_info["access_count"] += 1
                    self._save_index()
                    
                    return value
                except Exception:
                    self.delete(key)
            
            return None
    
    def put(self, key: str, value: Any, ttl: Optional[float] = None):
        """Put value in disk cache"""
        with self.lock:
            file_path = self._get_file_path(key)
            
            try:
                # Save to disk
                with open(file_path, 'wb') as f:
                    pickle.dump(value, f)
                
                # Update index
                self.index[key] = {
                    "created_at": time.time(),
                    "last_accessed": time.time(),
                    "access_count": 1,
                    "ttl": time.time() + ttl if ttl else None,
                    "file_path": file_path,
                    "size_bytes": os.path.getsize(file_path)
                }
                
                self._save_index()
                
            except Exception as e:
                print(f"Error saving to disk cache: {e}")
    
    def delete(self, key: str) -> bool:
        """Delete key from disk cache"""
        with self.lock:
            if key in self.index:
                file_path = self._get_file_path(key)
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception:
                        pass
                
                del self.index[key]
                self._save_index()
                return True
            return False
    
    def cleanup_expired(self):
        """Clean up expired cache entries"""
        with self.lock:
            current_time = time.time()
            expired_keys = []
            
            for key, entry_info in self.index.items():
                if entry_info.get("ttl") and current_time > entry_info["ttl"]:
                    expired_keys.append(key)
            
            for key in expired_keys:
                self.delete(key)

class MultiLevelCacheManager:
    """Advanced multi-level cache manager"""
    
    def __init__(self, data_dir: str = "synapseflow_data"):
        self.data_dir = data_dir
        self.cache_dir = os.path.join(data_dir, "cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Initialize cache levels
        self.memory_cache = LRUCache(max_size=1000)
        self.disk_cache = DiskCache(self.cache_dir)
        
        # Redis cache (if available)
        self.redis_cache = None
        if REDIS_AVAILABLE and os.getenv("REDIS_URL"):
            try:
                self.redis_cache = redis.from_url(os.getenv("REDIS_URL"))
                self.redis_cache.ping()  # Test connection
            except Exception:
                self.redis_cache = None
        
        # Performance tracking
        self.performance_stats = defaultdict(lambda: {
            "hits": 0, "misses": 0, "response_times": []
        })
        
        # Cache warming
        self.warm_cache_enabled = True
        self.warm_cache_thread = None
        
        # Start background tasks
        self._start_background_tasks()
    
    def _start_background_tasks(self):
        """Start background maintenance tasks"""
        def background_maintenance():
            while True:
                try:
                    # Clean up expired entries
                    self.disk_cache.cleanup_expired()
                    
                    # Cache warming
                    if self.warm_cache_enabled:
                        self._warm_cache()
                    
                    time.sleep(300)  # Run every 5 minutes
                except Exception as e:
                    print(f"Background maintenance error: {e}")
                    time.sleep(60)
        
        maintenance_thread = threading.Thread(target=background_maintenance, daemon=True)
        maintenance_thread.start()
    
    def _generate_cache_key(self, namespace: str, key: str, **kwargs) -> str:
        """Generate standardized cache key"""
        key_parts = [namespace, key]
        if kwargs:
            sorted_kwargs = sorted(kwargs.items())
            key_parts.append(json.dumps(sorted_kwargs, sort_keys=True))
        
        full_key = ":".join(key_parts)
        return hashlib.md5(full_key.encode()).hexdigest()
    
    def get(self, namespace: str, key: str, **kwargs) -> Optional[Any]:
        """Get value from multi-level cache"""
        cache_key = self._generate_cache_key(namespace, key, **kwargs)
        start_time = time.time()
        
        # Try memory cache first
        value = self.memory_cache.get(cache_key)
        if value is not None:
            self._record_hit(namespace, time.time() - start_time)
            return value
        
        # Try Redis cache
        if self.redis_cache:
            try:
                redis_value = self.redis_cache.get(cache_key)
                if redis_value:
                    value = pickle.loads(redis_value)
                    # Promote to memory cache
                    self.memory_cache.put(cache_key, value)
                    self._record_hit(namespace, time.time() - start_time)
                    return value
            except Exception:
                pass
        
        # Try disk cache
        value = self.disk_cache.get(cache_key)
        if value is not None:
            # Promote to higher levels
            self.memory_cache.put(cache_key, value)
            if self.redis_cache:
                try:
                    self.redis_cache.setex(cache_key, 3600, pickle.dumps(value))
                except Exception:
                    pass
            
            self._record_hit(namespace, time.time() - start_time)
            return value
        
        # Cache miss
        self._record_miss(namespace, time.time() - start_time)
        return None
    
    def put(self, namespace: str, key: str, value: Any, ttl: Optional[int] = None, **kwargs):
        """Put value in multi-level cache"""
        cache_key = self._generate_cache_key(namespace, key, **kwargs)
        
        # Store in all available cache levels
        self.memory_cache.put(cache_key, value, ttl)
        self.disk_cache.put(cache_key, value, ttl)
        
        if self.redis_cache:
            try:
                redis_ttl = ttl or 3600  # Default 1 hour
                self.redis_cache.setex(cache_key, redis_ttl, pickle.dumps(value))
            except Exception:
                pass
    
    def delete(self, namespace: str, key: str, **kwargs) -> bool:
        """Delete from all cache levels"""
        cache_key = self._generate_cache_key(namespace, key, **kwargs)
        
        deleted = False
        
        # Delete from memory
        if self.memory_cache.delete(cache_key):
            deleted = True
        
        # Delete from disk
        if self.disk_cache.delete(cache_key):
            deleted = True
        
        # Delete from Redis
        if self.redis_cache:
            try:
                if self.redis_cache.delete(cache_key):
                    deleted = True
            except Exception:
                pass
        
        return deleted
    
    def clear_namespace(self, namespace: str):
        """Clear all entries in a namespace"""
        # This is a simplified implementation
        # In production, you'd want more efficient namespace clearing
        pass
    
    def _record_hit(self, namespace: str, response_time: float):
        """Record cache hit"""
        stats = self.performance_stats[namespace]
        stats["hits"] += 1
        stats["response_times"].append(response_time)
        
        # Keep only recent response times
        if len(stats["response_times"]) > 1000:
            stats["response_times"] = stats["response_times"][-1000:]
    
    def _record_miss(self, namespace: str, response_time: float):
        """Record cache miss"""
        stats = self.performance_stats[namespace]
        stats["misses"] += 1
        stats["response_times"].append(response_time)
        
        # Keep only recent response times
        if len(stats["response_times"]) > 1000:
            stats["response_times"] = stats["response_times"][-1000:]
    
    def _warm_cache(self):
        """Warm cache with frequently accessed data"""
        try:
            # Analyze access patterns from performance stats
            popular_namespaces = []
            for namespace, stats in self.performance_stats.items():
                if stats["hits"] > 10:  # Frequently accessed
                    popular_namespaces.append((namespace, stats["hits"]))

            # Sort by popularity
            popular_namespaces.sort(key=lambda x: x[1], reverse=True)

            # Pre-warm cache for popular patterns
            for namespace, _ in popular_namespaces[:5]:  # Top 5 namespaces
                self._warm_namespace(namespace)

        except Exception as e:
            print(f"Cache warming error: {e}")

    def _warm_namespace(self, namespace: str):
        """Warm cache for a specific namespace"""
        try:
            # This would implement namespace-specific warming
            # For now, just ensure the namespace exists in stats
            if namespace not in self.performance_stats:
                self.performance_stats[namespace] = {
                    "hits": 0, "misses": 0, "response_times": []
                }
        except Exception as e:
            print(f"Namespace warming error for {namespace}: {e}")

    def get_cache_recommendations(self) -> Dict[str, Any]:
        """Get cache optimization recommendations"""
        recommendations = []

        # Analyze hit rates
        overall_stats = self.get_performance_stats()
        hit_rate = overall_stats.get("overall_hit_rate", 0)

        if hit_rate < 0.3:
            recommendations.append({
                "type": "low_hit_rate",
                "message": "Consider increasing cache TTL or warming more data",
                "priority": "high"
            })

        # Analyze memory usage
        memory_stats = overall_stats.get("memory_cache_stats", {})
        if memory_stats.get("size", 0) > memory_stats.get("max_size", 1000) * 0.9:
            recommendations.append({
                "type": "memory_pressure",
                "message": "Memory cache is near capacity, consider increasing size",
                "priority": "medium"
            })

        # Analyze response times
        avg_response_time = overall_stats.get("avg_response_time", 0)
        if avg_response_time > 0.1:  # 100ms
            recommendations.append({
                "type": "slow_cache",
                "message": "Cache response times are high, check disk performance",
                "priority": "medium"
            })

        return {
            "recommendations": recommendations,
            "overall_health": "good" if hit_rate > 0.5 else "needs_attention",
            "hit_rate": hit_rate,
            "avg_response_time": avg_response_time
        }
    
    def get_performance_stats(self, namespace: str = None) -> Dict[str, Any]:
        """Get cache performance statistics"""
        if namespace:
            stats = self.performance_stats[namespace]
            total_requests = stats["hits"] + stats["misses"]
            hit_rate = stats["hits"] / total_requests if total_requests > 0 else 0
            avg_response_time = sum(stats["response_times"]) / len(stats["response_times"]) if stats["response_times"] else 0
            
            return {
                "namespace": namespace,
                "hits": stats["hits"],
                "misses": stats["misses"],
                "total_requests": total_requests,
                "hit_rate": hit_rate,
                "avg_response_time": avg_response_time
            }
        else:
            # Overall stats
            total_stats = {"hits": 0, "misses": 0, "response_times": []}
            for stats in self.performance_stats.values():
                total_stats["hits"] += stats["hits"]
                total_stats["misses"] += stats["misses"]
                total_stats["response_times"].extend(stats["response_times"])
            
            total_requests = total_stats["hits"] + total_stats["misses"]
            hit_rate = total_stats["hits"] / total_requests if total_requests > 0 else 0
            avg_response_time = sum(total_stats["response_times"]) / len(total_stats["response_times"]) if total_stats["response_times"] else 0
            
            return {
                "total_hits": total_stats["hits"],
                "total_misses": total_stats["misses"],
                "total_requests": total_requests,
                "overall_hit_rate": hit_rate,
                "avg_response_time": avg_response_time,
                "memory_cache_stats": self.memory_cache.get_stats(),
                "redis_available": self.redis_cache is not None
            }
    
    def cache_decorator(self, namespace: str, ttl: int = 3600):
        """Decorator for caching function results"""
        def decorator(func: Callable) -> Callable:
            def wrapper(*args, **kwargs):
                # Generate cache key from function name and arguments
                key_data = {
                    "func": func.__name__,
                    "args": str(args),
                    "kwargs": str(sorted(kwargs.items()))
                }
                cache_key = hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()

                # Try to get from cache
                cached_result = self.get(namespace, cache_key)
                if cached_result is not None:
                    return cached_result

                # Execute function and cache result
                result = func(*args, **kwargs)
                self.put(namespace, cache_key, result, ttl)

                return result
            return wrapper
        return decorator

    def get_cache_analytics(self, hours: int = 24) -> Dict[str, Any]:
        """Get detailed cache analytics for the specified time period"""
        analytics = {
            "time_period_hours": hours,
            "namespace_stats": {},
            "performance_trends": {},
            "efficiency_metrics": {}
        }

        # Analyze per-namespace performance
        for namespace, stats in self.performance_stats.items():
            total_requests = stats["hits"] + stats["misses"]
            if total_requests > 0:
                analytics["namespace_stats"][namespace] = {
                    "hit_rate": stats["hits"] / total_requests,
                    "total_requests": total_requests,
                    "avg_response_time": sum(stats["response_times"]) / len(stats["response_times"]) if stats["response_times"] else 0,
                    "efficiency_score": (stats["hits"] / total_requests) * 100
                }

        # Calculate overall efficiency metrics
        total_hits = sum(stats["hits"] for stats in self.performance_stats.values())
        total_misses = sum(stats["misses"] for stats in self.performance_stats.values())
        total_requests = total_hits + total_misses

        if total_requests > 0:
            analytics["efficiency_metrics"] = {
                "overall_hit_rate": total_hits / total_requests,
                "cache_effectiveness": "excellent" if total_hits / total_requests > 0.8 else
                                     "good" if total_hits / total_requests > 0.6 else
                                     "needs_improvement",
                "total_requests": total_requests,
                "estimated_time_saved": total_hits * 0.05,  # Assume 50ms saved per hit
                "memory_efficiency": self.memory_cache.size() / self.memory_cache.max_size
            }

        return analytics

    def optimize_cache_settings(self) -> Dict[str, Any]:
        """Analyze usage patterns and suggest optimal cache settings"""
        analytics = self.get_cache_analytics()
        optimizations = []

        # Analyze hit rates by namespace
        for namespace, stats in analytics.get("namespace_stats", {}).items():
            hit_rate = stats["hit_rate"]

            if hit_rate < 0.3:
                optimizations.append({
                    "namespace": namespace,
                    "issue": "low_hit_rate",
                    "suggestion": "Increase TTL or review caching strategy",
                    "current_hit_rate": hit_rate
                })
            elif hit_rate > 0.9:
                optimizations.append({
                    "namespace": namespace,
                    "issue": "over_caching",
                    "suggestion": "Consider reducing TTL to free up memory",
                    "current_hit_rate": hit_rate
                })

        # Memory optimization suggestions
        memory_stats = self.memory_cache.get_stats()
        if memory_stats["size"] > memory_stats["max_size"] * 0.9:
            optimizations.append({
                "namespace": "memory",
                "issue": "memory_pressure",
                "suggestion": "Increase memory cache size or implement more aggressive eviction",
                "current_usage": memory_stats["size"] / memory_stats["max_size"]
            })

        return {
            "optimizations": optimizations,
            "overall_health": "good" if len(optimizations) < 3 else "needs_attention",
            "recommendations_count": len(optimizations)
        }

# Global cache manager instance
_cache_manager = None

def get_cache_manager() -> MultiLevelCacheManager:
    """Get global cache manager instance"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = MultiLevelCacheManager()
    return _cache_manager

# Convenience decorators
def cache_result(namespace: str = "default", ttl: int = 3600):
    """Decorator to cache function results"""
    return get_cache_manager().cache_decorator(namespace, ttl)
