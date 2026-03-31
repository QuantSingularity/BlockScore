"""
Cache Manager for BlockScore Backend
Redis-based caching for performance optimization
"""

import hashlib
import json
import logging
import pickle
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Dict, List, Optional, Union

import redis


class CacheManager:
    """Redis-based cache manager with advanced features"""

    def __init__(
        self,
        redis_client: Optional[redis.Redis] = None,
        default_ttl: int = 3600,
        key_prefix: str = "blockscore",
    ) -> None:
        self.redis = redis_client
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix
        self.logger = logging.getLogger(__name__)
        self.stats = {"hits": 0, "misses": 0, "sets": 0, "deletes": 0}
        self.serializers = {
            "json": (json.dumps, json.loads),
            "pickle": (pickle.dumps, pickle.loads),
        }

    def is_available(self) -> bool:
        """Check if Redis cache is available"""
        if not self.redis:
            return False
        try:
            self.redis.ping()
            return True
        except Exception as e:
            self.logger.warning(f"Cache not available: {e}")
            return False

    def get(self, key: str, default: Any = None, serializer: str = "json") -> Any:
        """Get value from cache"""
        if not self.is_available():
            return default
        try:
            cache_key = self._build_key(key)
            value = self.redis.get(cache_key)
            if value is None:
                self.stats["misses"] += 1
                return default
            _, deserialize = self.serializers.get(serializer, self.serializers["json"])
            result = deserialize(value)
            self.stats["hits"] += 1
            return result
        except Exception as e:
            self.logger.error(f"Cache get error for key {key}: {e}")
            self.stats["misses"] += 1
            return default

    def set(
        self, key: str, value: Any, ttl: Optional[int] = None, serializer: str = "json"
    ) -> bool:
        """Set value in cache"""
        if not self.is_available():
            return False
        try:
            cache_key = self._build_key(key)
            ttl = ttl or self.default_ttl
            serialize, _ = self.serializers.get(serializer, self.serializers["json"])
            serialized_value = serialize(value)
            result = self.redis.setex(cache_key, ttl, serialized_value)
            if result:
                self.stats["sets"] += 1
            return result
        except Exception as e:
            self.logger.error(f"Cache set error for key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.is_available():
            return False
        try:
            cache_key = self._build_key(key)
            result = self.redis.delete(cache_key)
            if result:
                self.stats["deletes"] += 1
            return bool(result)
        except Exception as e:
            self.logger.error(f"Cache delete error for key {key}: {e}")
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self.is_available():
            return False
        try:
            cache_key = self._build_key(key)
            return bool(self.redis.exists(cache_key))
        except Exception as e:
            self.logger.error(f"Cache exists error for key {key}: {e}")
            return False

    def expire(self, key: str, ttl: int) -> bool:
        """Set expiration time for key"""
        if not self.is_available():
            return False
        try:
            cache_key = self._build_key(key)
            return bool(self.redis.expire(cache_key, ttl))
        except Exception as e:
            self.logger.error(f"Cache expire error for key {key}: {e}")
            return False

    def ttl(self, key: str) -> int:
        """Get time to live for key"""
        if not self.is_available():
            return -1
        try:
            cache_key = self._build_key(key)
            return self.redis.ttl(cache_key)
        except Exception as e:
            self.logger.error(f"Cache TTL error for key {key}: {e}")
            return -1

    def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern"""
        if not self.is_available():
            return 0
        try:
            cache_pattern = self._build_key(pattern)
            keys = self.redis.keys(cache_pattern)
            if keys:
                deleted = self.redis.delete(*keys)
                self.stats["deletes"] += deleted
                return deleted
            return 0
        except Exception as e:
            self.logger.error(f"Cache clear pattern error for {pattern}: {e}")
            return 0

    def clear_all(self) -> bool:
        """Clear all cache keys with prefix"""
        if not self.is_available():
            return False
        try:
            pattern = f"{self.key_prefix}:*"
            keys = self.redis.keys(pattern)
            if keys:
                deleted = self.redis.delete(*keys)
                self.stats["deletes"] += deleted
                return True
            return True
        except Exception as e:
            self.logger.error(f"Cache clear all error: {e}")
            return False

    def get_multi(self, keys: List[str], serializer: str = "json") -> Dict[str, Any]:
        """Get multiple values from cache"""
        if not self.is_available():
            return {}
        try:
            cache_keys = [self._build_key(key) for key in keys]
            values = self.redis.mget(cache_keys)
            _, deserialize = self.serializers.get(serializer, self.serializers["json"])
            result = {}
            for i, (key, value) in enumerate(zip(keys, values)):
                if value is not None:
                    try:
                        result[key] = deserialize(value)
                        self.stats["hits"] += 1
                    except Exception as e:
                        self.logger.error(f"Deserialization error for key {key}: {e}")
                        self.stats["misses"] += 1
                else:
                    self.stats["misses"] += 1
            return result
        except Exception as e:
            self.logger.error(f"Cache get_multi error: {e}")
            self.stats["misses"] += len(keys)
            return {}

    def set_multi(
        self, data: Dict[str, Any], ttl: Optional[int] = None, serializer: str = "json"
    ) -> bool:
        """Set multiple values in cache"""
        if not self.is_available():
            return False
        try:
            ttl = ttl or self.default_ttl
            serialize, _ = self.serializers.get(serializer, self.serializers["json"])
            pipe = self.redis.pipeline()
            for key, value in data.items():
                cache_key = self._build_key(key)
                serialized_value = serialize(value)
                pipe.setex(cache_key, ttl, serialized_value)
            results = pipe.execute()
            success_count = sum((1 for result in results if result))
            self.stats["sets"] += success_count
            return success_count == len(data)
        except Exception as e:
            self.logger.error(f"Cache set_multi error: {e}")
            return False

    def increment(
        self, key: str, amount: int = 1, ttl: Optional[int] = None
    ) -> Optional[int]:
        """Increment counter in cache"""
        if not self.is_available():
            return None
        try:
            cache_key = self._build_key(key)
            pipe = self.redis.pipeline()
            pipe.incr(cache_key, amount)
            if ttl:
                pipe.expire(cache_key, ttl)
            results = pipe.execute()
            return results[0]
        except Exception as e:
            self.logger.error(f"Cache increment error for key {key}: {e}")
            return None

    def decrement(self, key: str, amount: int = 1) -> Optional[int]:
        """Decrement counter in cache"""
        if not self.is_available():
            return None
        try:
            cache_key = self._build_key(key)
            return self.redis.decr(cache_key, amount)
        except Exception as e:
            self.logger.error(f"Cache decrement error for key {key}: {e}")
            return None

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_operations = sum(self.stats.values())
        hit_rate = (
            self.stats["hits"] / (self.stats["hits"] + self.stats["misses"]) * 100
            if self.stats["hits"] + self.stats["misses"] > 0
            else 0
        )
        stats = {
            "operations": self.stats.copy(),
            "total_operations": total_operations,
            "hit_rate": round(hit_rate, 2),
            "available": self.is_available(),
        }
        if self.is_available():
            try:
                redis_info = self.redis.info()
                stats["redis_info"] = {
                    "used_memory": redis_info.get("used_memory_human"),
                    "connected_clients": redis_info.get("connected_clients"),
                    "total_commands_processed": redis_info.get(
                        "total_commands_processed"
                    ),
                    "keyspace_hits": redis_info.get("keyspace_hits"),
                    "keyspace_misses": redis_info.get("keyspace_misses"),
                }
            except Exception as e:
                self.logger.error(f"Error getting Redis info: {e}")
        return stats

    def health_check(self) -> Dict[str, Any]:
        """Perform cache health check"""
        health = {"available": False, "latency_ms": None, "error": None}
        if not self.is_available():
            health["error"] = "Redis not available"
            return health
        try:
            start_time = datetime.now()
            test_key = f"health_check_{int(start_time.timestamp())}"
            self.redis.set(test_key, "test", ex=10)
            value = self.redis.get(test_key)
            self.redis.delete(test_key)
            end_time = datetime.now()
            latency = (end_time - start_time).total_seconds() * 1000
            health["available"] = value == b"test"
            health["latency_ms"] = round(latency, 2)
        except Exception as e:
            health["error"] = str(e)
        return health

    def _build_key(self, key: str) -> str:
        """Build cache key with prefix"""
        return f"{self.key_prefix}:{key}"

    def _hash_key(self, data: Union[str, Dict, List]) -> str:
        """Generate hash for complex keys"""
        if isinstance(data, str):
            return data
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.md5(json_str.encode()).hexdigest()


def cached(
    cache_manager: CacheManager,
    ttl: int = 3600,
    key_prefix: str = "",
    serializer: str = "json",
) -> Any:
    """Decorator to cache function results"""

    def decorator(func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            key_data = {"function": func.__name__, "args": args, "kwargs": kwargs}
            cache_key = (
                f"{key_prefix}:{cache_manager._hash_key(key_data)}"
                if key_prefix
                else cache_manager._hash_key(key_data)
            )
            result = cache_manager.get(cache_key, serializer=serializer)
            if result is not None:
                return result
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl=ttl, serializer=serializer)
            return result

        wrapper.cache_clear = lambda: cache_manager.clear_pattern(
            f"{key_prefix}:*" if key_prefix else "*"
        )
        wrapper.cache_key = lambda *args, **kwargs: cache_manager._hash_key(
            {"function": func.__name__, "args": args, "kwargs": kwargs}
        )
        return wrapper

    return decorator


def cache_invalidate(cache_manager: CacheManager, patterns: List[str]) -> Any:
    """Decorator to invalidate cache patterns after function execution"""

    def decorator(func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            for pattern in patterns:
                cache_manager.clear_pattern(pattern)
            return result

        return wrapper

    return decorator


class CacheWarmer:
    """Utility for warming up cache with frequently accessed data"""

    def __init__(self, cache_manager: CacheManager) -> None:
        self.cache = cache_manager
        self.logger = logging.getLogger(__name__)

    def warm_user_data(self, user_ids: List[str]) -> Dict[str, Any]:
        """Warm cache with user data"""
        results = {"success": 0, "failed": 0}
        for user_id in user_ids:
            try:
                cache_key = f"user:{user_id}"
                if not self.cache.exists(cache_key):
                    user_data = {
                        "id": user_id,
                        "cached_at": datetime.now(timezone.utc).isoformat(),
                    }
                    if self.cache.set(cache_key, user_data, ttl=3600):
                        results["success"] += 1
                    else:
                        results["failed"] += 1
            except Exception as e:
                self.logger.error(f"Cache warming failed for user {user_id}: {e}")
                results["failed"] += 1
        return results

    def warm_credit_scores(self, user_ids: List[str]) -> Dict[str, Any]:
        """Warm cache with credit score data"""
        results = {"success": 0, "failed": 0}
        for user_id in user_ids:
            try:
                cache_key = f"credit_score:{user_id}"
                if not self.cache.exists(cache_key):
                    score_data = {
                        "user_id": user_id,
                        "score": 750,
                        "cached_at": datetime.now(timezone.utc).isoformat(),
                    }
                    if self.cache.set(cache_key, score_data, ttl=1800):
                        results["success"] += 1
                    else:
                        results["failed"] += 1
            except Exception as e:
                self.logger.error(
                    f"Credit score cache warming failed for user {user_id}: {e}"
                )
                results["failed"] += 1
        return results
