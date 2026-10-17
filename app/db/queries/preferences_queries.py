
GET_USER_PREFERENCES = """
SELECT currency_display
FROM user_preferences
WHERE user_id = %s
"""

UPSERT_USER_PREFERENCES = """
INSERT INTO user_preferences (user_id, currency_display)
VALUES (%s, %s)
ON DUPLICATE KEY UPDATE currency_display = VALUES(currency_display)
"""
