
from app.services.redis_service import redis_client


def format_redis_key(user_id: str, token_type: str = "access_token") -> str:
    """Format a Redis key for a user's token."""
    return f"user:{user_id}:{token_type}"


async def store_access_token_in_redis(
    user_id: str,
    access_token: str,
    expiration_seconds: int = 3600,
) -> None:
    """Store an access token with an expiration."""
    redis_key = format_redis_key(user_id, "access_token")
    await redis_client.set(redis_key, access_token, ex=expiration_seconds)


async def get_access_token_from_redis(user_id: str) -> str | None:
    """Retrieve a user's stored access token."""
    redis_key = format_redis_key(user_id, "access_token")
    return await redis_client.get(redis_key)


async def delete_access_token_from_redis(user_id: str) -> int:
    """Delete a user's stored access token. Returns the number of keys deleted."""
    redis_key = format_redis_key(user_id, "access_token")
    return await redis_client.delete(redis_key)


async def access_token_exists_in_redis(user_id: str) -> bool:
    """Check whether a user's access token exists."""
    redis_key = format_redis_key(user_id, "access_token")
    return bool(await redis_client.exists(redis_key))


async def get_access_token_ttl(user_id: str) -> int:
    """Return remaining token lifetime in seconds."""
    redis_key = format_redis_key(user_id, "access_token")
    return await redis_client.ttl(redis_key)
