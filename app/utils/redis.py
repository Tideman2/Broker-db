
from app.services.redis_service import redis_client
from app.utils.otp import OTP_INTERVAL
from app.Models.auth_models import UserRole

# SESSION TOKEN MANAGEMENT


def format_redis_key(
        user_id: str,
        token_type: str = "access_token",
        role: UserRole = UserRole.USER
) -> str:
    """Format a Redis key for a user's token."""
    suffix = role.value if isinstance(role, UserRole) else str(role)
    return f"user:{user_id}:{token_type}:{suffix}"


async def store_access_token_in_redis(
    user_id: str,
    access_token: str,
    expiration_seconds: int = 3600,
    user_role: UserRole = UserRole.USER
) -> None:
    """Store an access token with an expiration."""
    redis_key = format_redis_key(user_id, "access_token", user_role)
    await redis_client.set(redis_key, access_token, ex=expiration_seconds)


async def get_access_token_from_redis(user_id: str, user_role: UserRole = UserRole.USER) -> str | None:
    """Retrieve a user's stored access token."""
    redis_key = format_redis_key(user_id, "access_token", user_role)
    return await redis_client.get(redis_key)


async def delete_access_token_from_redis(user_id: str, user_role: UserRole = UserRole.USER) -> int:
    """Delete a user's stored access token. Returns the number of keys deleted."""
    redis_key = format_redis_key(user_id, "access_token", user_role)
    return await redis_client.delete(redis_key)


async def access_token_exists_in_redis(user_id: str, user_role: UserRole = UserRole.USER) -> bool:
    """Check whether a user's access token exists."""
    redis_key = format_redis_key(user_id, "access_token", user_role)
    return bool(await redis_client.exists(redis_key))


async def get_access_token_ttl(user_id: str, user_role: UserRole = UserRole.USER) -> int:
    """Return remaining token lifetime in seconds."""
    redis_key = format_redis_key(user_id, "access_token", user_role)
    return await redis_client.ttl(redis_key)

# OTP TOKEN MANAGEMENT


async def store_otp_secret_redis(
    user_id: str,
    secret: str,
    expiration_seconds: int = OTP_INTERVAL,
    user_role: UserRole = UserRole.USER
) -> None:
    """Store an OTP secret with an expiration."""
    redis_key = format_redis_key(user_id, "otp", user_role)
    await redis_client.set(redis_key, secret, ex=expiration_seconds)


async def get_otp_secret_redis(user_id: str, user_role: UserRole = UserRole.USER) -> str | None:
    """Retrieve a user's stored OTP secret."""
    redis_key = format_redis_key(user_id, "otp", user_role)
    return await redis_client.get(redis_key)


async def delete_otp_secret_redis(user_id: str, user_role: UserRole = UserRole.USER) -> int:
    """Delete a user's stored OTP secret. Returns the number of keys deleted."""
    redis_key = format_redis_key(user_id, "otp", user_role)
    return await redis_client.delete(redis_key)


# RESET PASSWORD TOKEN MANAGEMENT

async def store_reset_password_token_redis(
    user_id: str,
    token: str,
    expiration_seconds: int = 3600,
    user_role: UserRole = UserRole.USER
) -> None:
    """Store a reset password token with an expiration."""
    redis_key = format_redis_key(user_id, "reset_password_token", user_role)
    await redis_client.set(redis_key, token, ex=expiration_seconds)


async def get_reset_password_token_redis(
        user_id: str,
        user_role: UserRole = UserRole.USER
) -> str | None:
    """Retrieve a user's stored reset password token."""
    redis_key = format_redis_key(user_id, "reset_password_token", user_role)
    return await redis_client.get(redis_key)


async def delete_reset_password_token_redis(
        user_id: str,
        user_role: UserRole = UserRole.USER
) -> int:
    """Delete a user's stored reset password token. Returns the number of keys deleted."""
    redis_key = format_redis_key(user_id, "reset_password_token", user_role)
    return await redis_client.delete(redis_key)
