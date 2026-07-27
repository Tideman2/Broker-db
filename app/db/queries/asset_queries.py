GET_ASSET = """
SELECT *
FROM assets
WHERE id = %s
"""

GET_ASSETS = """
SELECT *
FROM assets
ORDER BY id
"""

ADD_ASSET = """
INSERT INTO assets (
    symbol,
    name,
    address,
    is_active
) VALUES ( %s, %s, %s, %s );
"""

UPDATE_ASSET = """
UPDATE assets
SET
    symbol = %s,
    name = %s,
    address = %s,
    is_active = %s
WHERE id = %s
"""

DELETE_ASSET = """
DELETE FROM assets
WHERE id = %s
"""

GET_ASSET_BY_SYMBOL = """
SELECT *
FROM assets
WHERE symbol = %s
"""

GET_ACTIVE_ASSETS = """
SELECT *
FROM assets
WHERE is_active = TRUE
ORDER BY symbol
"""
