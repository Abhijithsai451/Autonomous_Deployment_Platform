from typing import Optional
from redis.asyncio import Redis, ConnectionPool
from packages.config.settings import common_settings
from packages.logging.structured_logs import struc_logger as logger

class RedisClientConfig:
    """
    Manages the Lifecycle, Connection, and Health
    """
    def __init__(self, redis_url: Optional[str]=None):
        self.redis_url = redis_url or common_settings.REDIS_URL
        self._pool :  Optional[ConnectionPool]=None
        self._client: Optional[Redis] = None

    async def initialize(self)-> None:
        """Initializes the connection pool and verifies connection """
        if self._client is None:
            logger.info(f"Connecting to Redis at: {self.redis_url}")

            client = Redis.from_url(
                self.redis_url,
                max_connections=common_settings.REDIS_MAX_CONNECTIONS,
                decode_responses=True,
                socket_timeout=common_settings.REDIS_TIMEOUT,
            )
            try:
                pong = await client.ping()
                if not pong:
                    raise RuntimeError("Redis ping returned False")
                self._client = client
            except Exception as exc:
                await client.aclose()
                logger.error(f"Failed to connect to Redis at {self.redis_url}: {exc}")
                raise RuntimeError(f"Failed to connect to Redis Client at {self.redis_url} - Error: {exc}") from exc

            logger.info("Redis client and connection pool successfully initialized.")
    @property
    def client(self)-> Redis:
        if self._client is None:
            raise RuntimeError("Redis Client is not initialized. Call '.initialize()")
        return self._client

    async def check_health(self)-> bool:
        """Pings Redis to confirm cluster/node availability."""
        try:
            if self._client:
                return await self._client.ping()
        except Exception as exc:
            logger.error(f"Redis health check failed: {exc}")
            return False
        return False

    async def close(self) -> None:
        """Gracefully drains and closes connection pools on app shutdown."""
        if self._client:
            await self._client.aclose()
            self._client = None
        if self._pool:
            await self._pool.disconnect()
            self._pool = None
        logger.info("Redis client connection pool closed cleanly.")

redis_client = RedisClientConfig()


