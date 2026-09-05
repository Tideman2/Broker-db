
INSERT_USER = """
INSERT INTO users (
    email, full_name, phone, dob, username, accept_terms, marketing_opt_in, password_hash
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
"""

GET_USER_BY_ID = """
SELECT *
FROM users
JOIN user_addresses ON users.id = user_addresses.user_id
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
