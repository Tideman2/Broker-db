from app.utils.redis import format_redis_key
from app.Models.auth_models import UserRole


class TestFormatRedisKey:
    def test_role_enum_and_string_produce_same_user_key(self):
        assert (
            format_redis_key("1", "access_token", UserRole.USER)
            == format_redis_key("1", "access_token", "USER")
        )

    def test_role_enum_and_string_produce_same_admin_key(self):
        assert (
            format_redis_key("1", "access_token", UserRole.ADMIN)
            == format_redis_key("1", "access_token", "ADMIN")
        )

    def test_user_and_admin_keys_differ(self):
        assert format_redis_key(
            "1", "access_token", "USER"
        ) != format_redis_key("1", "access_token", "ADMIN")
