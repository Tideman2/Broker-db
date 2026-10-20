import os

import redis.asyncio as redis


redis_url = os.getenv("REDIS_URL")

if redis_url:
    redis_client = redis.Redis.from_url(
        redis_url,
        decode_responses=True,
    )
else:
    redis_client = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        decode_responses=True,
    )


async def close_redis():
    await redis_client.aclose()
