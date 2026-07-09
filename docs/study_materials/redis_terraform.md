# Caching with Redis & Infrastructure as Code (Terraform)

This guide bridges the gap between architectural caching patterns and automated infrastructure deployment.

---

## 1. Architectural Foundation: The Cache Aside Pattern
Caching is not just "storing data"; it is about optimizing the path between your application and the database.


* **Cache Aside (Lazy Loading):** The application checks the cache. If it's a miss, it fetches from the DB, populates the cache, and returns the result.
* **Write-Through/Write-Behind:** Strategies for high-consistency requirements.
* **Eviction Policies:** Redis is not infinite. Understanding `allkeys-lru` (Least Recently Used) versus `volatile-lru` is critical for memory management.

---

## 2. Infrastructure as Code: Terraform
Deploying a Redis instance (e.g., AWS ElastiCache) manually is prone to configuration drift. Terraform ensures idempotency.

```hcl
# main.tf - Defining an ElastiCache Cluster
resource "aws_elasticache_cluster" "main" {
  cluster_id           = "apps-cache-cluster"
  engine               = "redis"
  node_type            = "cache.t4g.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379
}
```

---

## 3. Redis Performance & Python Integration
When using `redis-py` in production, connection management is the primary bottleneck.

### Asynchronous Connection Pooling
Using `redis-py` with `asyncio` allows for non-blocking I/O, which is essential for high-throughput microservices.

```python
import redis.asyncio as redis
import json

# Connection Pooling is non-negotiable for performance
pool = redis.ConnectionPool(host='localhost', port=6379, db=0, max_connections=20)
r = redis.Redis(connection_pool=pool)

async def get_user_data(user_id):
    cache_key = f"user:{user_id}"
    
    # Try cache
    cached_data = await r.get(cache_key)
    if cached_data:
        return json.loads(cached_data)
    
    # Cache miss: Fetch from DB (Simulated)
    user_data = {"id": user_id, "name": "Jane Doe"} # Assume DB fetch here
    
    # Populate cache with TTL (Time To Live) to prevent stale data
    await r.setex(cache_key, 3600, json.dumps(user_data))
    return user_data
```

---

## 4. Advanced Concepts
* **Redis Transactions (MULTI/EXEC):** Redis supports atomicity within a transaction block. Use these to ensure multiple keys are updated simultaneously.
* **Lua Scripting:** Offload complex logic from the application server to the Redis server itself to reduce network round-trips.
* **Persistence Strategy:** Choose between RDB (point-in-time snapshots) and AOF (append-only log). AOF is more durable but heavier on I/O.
* **Terraform State Management:** Never store `.tfstate` locally in production. Use an S3 backend with DynamoDB locking.

---

## 5. Summary & Checklist for Production
* [ ] **TTL Strategy:** Every cached item must have a TTL.
* [ ] **Serialization:** Use binary formats (MessagePack/Protobuf) for large payloads to minimize memory footprint.
* [ ] **Circuit Breaker:** Wrap cache calls in a circuit breaker pattern; if Redis goes down, the system should gracefully fallback to the database.
* [ ] **Monitoring:** Track `keyspace_hits` vs `keyspace_misses`. A hit rate below 80% often signals a poorly chosen cache key strategy.
