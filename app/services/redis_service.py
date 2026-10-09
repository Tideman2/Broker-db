
import os

import redis.asyncio as redis


redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True,
)


async def close_redis():
    await redis_client.aclose()
