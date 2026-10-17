
INSERT_USER = """
INSERT INTO users (
    email, full_name, phone, dob, username, accept_terms, marketing_opt_in, password_hash
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
"""

GET_USER_BY_ID = """
SELECT
    users.id AS user_id,
    users.email AS email,
    users.full_name AS full_name,
    users.phone AS phone,
    users.dob AS dob,
    users.username AS username,
    users.role AS role,
    user_addresses.country AS country,
    user_addresses.city AS city,
    user_addresses.state AS state,
    user_addresses.zip AS zip,
    user_addresses.address1 AS address1,
    user_addresses.address2 AS address2
FROM users
LEFT JOIN user_addresses ON users.id = user_addresses.user_id
WHERE users.id = %s;
"""

GET_USER_BY_EMAIL = """
SELECT *
FROM users
WHERE email = %s
"""

INSERT_ADDRESS = """
INSERT INTO user_addresses (
    user_id, address1, address2, city, state, zip, country
) VALUES (%s, %s, %s, %s, %s, %s, %s)
"""

DELETE_USER = """
DELETE 
FROM users
WHERE id = %s
"""

GET_ALL_USERS = """
SELECT id, email, full_name, username, role, created_at
FROM users
ORDER BY created_at DESC
LIMIT %s OFFSET %s
"""

USER_EXISTS = """
SELECT id
FROM users
WHERE id = %s
"""

UPDATE_USER_FULL_NAME = """
UPDATE users
SET full_name = %s
WHERE id = %s
"""

GET_USER_PASSWORD_HASH = """
SELECT id, password_hash
FROM users
WHERE id = %s
"""

UPDATE_USER_PASSWORD = """
UPDATE users
SET password_hash = %s
WHERE id = %s
"""
