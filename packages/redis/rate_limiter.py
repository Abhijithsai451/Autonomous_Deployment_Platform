import time
from packages.redis.redis_client import redis_client
from packages.logging.structured_logs import struc_logger as logger

class SlidingWindowRateLimiter:
    """Sliding-window rate limiter backed by Redis sorted sets (ZSET)."""
    def __init__(self, key_prefix: str = "cortexops:ratelimit"):
        self.key_prefix = key_prefix

    async def is_allowed(self, identifier: str, max_requests: int, window_seconds: int) -> bool:
        """Determines if a request passes the rate limit threshold."""
        key = f"{self.key_prefix}:{identifier}"
        now = time.time()
        window_start = now - window_seconds

        lua_script = """
            local key = KEYS[1]
            local now = tonumber(ARGV[1])
            local window_start = tonumber(ARGV[2])
            local max_requests = tonumber(ARGV[3])
            local window_seconds = tonumber(ARGV[4])

            -- Remove timestamps outside the sliding window
            redis.call('ZREMRANGEBYSCORE', key, 0, window_start)

            -- Count remaining requests
            local current_requests = redis.call('ZCARD', key)

            if current_requests < max_requests then
                redis.call('ZADD', key, now, now)
                redis.call('EXPIRE', key, window_seconds)
                return 1
            else
                return 0
            end
        """
        try:
            res = await redis_client.client.eval(
                lua_script, 1, key, now, window_start, max_requests, window_seconds
            )
            return res == 1
        except Exception as exc:
            logger.error(f"Rate limiter check failed for '{identifier}': {exc}")
            # Fail-open strategy to prevent blocking traffic during Redis failures
            return True