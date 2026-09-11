import uuid
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from packages.redis.redis_client import redis_client
from packages.logging.structured_logs import struc_logger as logger

class LockAcquisitionError(Exception):
    """Raised when a distributed lock cannot be acquired within the timeout."""
    pass

class DistributedLock:
    """Distributed locking mechanism backed by Redis."""
    def __init__(self, name: str, ttl_seconds: int = 10):
        self.name = f"cortexops:lock:{name}"
        self.ttl = ttl_seconds
        self.identifier = str(uuid.uuid4())

    async def acquire(self, retry_interval: float = 0.1, timeout: float = 5.0) -> bool:
        """Attempts to acquire the lock within the specified timeout."""
        start_time = asyncio.get_event_loop().time()
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            acquired = await redis_client.client.set(
                self.name, self.identifier, ex=self.ttl, nx=True
            )
            if acquired:
                return True
            await asyncio.sleep(retry_interval)
        return False

    async def release(self) -> None:
        """Releases the lock safely using a Lua script to prevent unlocking foreign locks."""
        lua_release = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
        """
        try:
            await redis_client.client.eval(lua_release, 1, self.name, self.identifier)
        except Exception as exc:
            logger.error(f"Error releasing Redis lock '{self.name}': {exc}")

@asynccontextmanager
async def lock(
    name: str, ttl_seconds: int = 10, timeout: float = 5.0
) -> AsyncGenerator[None, None]:
    """Context manager helper for safe locking execution."""
    dist_lock = DistributedLock(name, ttl_seconds)
    acquired = await dist_lock.acquire(timeout=timeout)
    if not acquired:
        raise LockAcquisitionError(f"Could not acquire lock for resource '{name}' within {timeout}s")
    try:
        yield
    finally:
        await dist_lock.release()