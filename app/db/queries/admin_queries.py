

GET_ADMIN_BY_EMAIL = """
SELECT *
FROM admins
WHERE email = %s
"""

INSERT_ADMIN = """
INSERT INTO admins (
email,
password_hash
)
VALUES (
%s,
%s
)
"""

DELETE_ADMIN = """
DELETE FROM admins
WHERE id = %s
"""

UPDATE_ADMIN = """
UPDATE admins
SET
    email = %s,
    password = %s,
WHERE id = %s
"""
