import json
from typing import Optional, Any, Type, TypeVar

from pydantic import BaseModel

from packages.logging.structured_logs import struc_logger as logger
from packages.redis.redis_client import redis_client

T = TypeVar("T", bound=BaseModel)
class RedisCache:
    def __init__(self, key_prefix: str = "cortexops"):
        self.key_prefix = key_prefix

    def _build_key(self, key: str) -> str:
        return f"{self.key_prefix}:{key}"

    async def get(self, key: str) -> Optional[Any]:
        """Retrieves raw JSON/string data from cache."""
        full_key = self._build_key(key)
        try:
            val = await redis_client.client.get(full_key)
            return json.loads(val) if val else None
        except Exception as exc:
            logger.error(f"Redis GET failed for key '{full_key}': {exc}")
            return None

    async def get_model(self, key: str, model_cls: Type[T]) -> Optional[T]:
        """Retrieves and deserializes data directly into a Pydantic model."""
        data = await self.get(key)
        if data:
            try:
                return model_cls.model_validate(data)
            except Exception as exc:
                logger.error(f"Failed to validate cached model for key '{key}': {exc}")
                return None
        return None

    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = 300) -> bool:
        """Serializes and sets a value in Redis with an optional TTL."""
        full_key = self._build_key(key)
        try:
            if isinstance(value, BaseModel):
                serialized = value.model_dump_json()
            else:
                serialized = json.dumps(value)

            if ttl_seconds:
                await redis_client.client.setex(full_key, ttl_seconds, serialized)
            else:
                await redis_client.client.set(full_key, serialized)
            return True
        except Exception as exc:
            logger.error(f"Redis SET failed for key '{full_key}': {exc}")
            return False

    async def delete(self, key: str) -> bool:
        """Deletes a specific key."""
        full_key = self._build_key(key)
        try:
            await redis_client.client.delete(full_key)
            return True
        except Exception as exc:
            logger.error(f"Redis DELETE failed for key '{full_key}': {exc}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """Invalidates all keys matching a wild-card pattern (e.g., 'tenant:123:*')."""
        full_pattern = f"{self.key_prefix}:{pattern}"
        deleted_count = 0
        try:
            async for key in redis_client.client.scan_iter(match=full_pattern):
                await redis_client.client.delete(key)
                deleted_count += 1
            logger.info(f"Purged {deleted_count} cache keys matching pattern '{full_pattern}'")
            return deleted_count
        except Exception as exc:
            logger.error(f"Redis delete_pattern failed for '{full_pattern}': {exc}")
            return 0