
CHECK_INSTRUMENT = """
SELECT id, current_price
FROM instruments
WHERE id = %s
AND is_active = TRUE;
"""

CHECK_INSTRUMENT_ANY = """
SELECT id, current_price
FROM instruments
WHERE id = %s;
"""

GET_USER_INSTRUMENT_TRANSACTIONS = """
SELECT
    type,
    quantity,
    price,
    executed_at
FROM transactions
WHERE
    user_id = %s
AND
    instrument_id = %s
ORDER BY executed_at
"""

GET_INSTRUMENT_RISK_WEIGHT = """
SELECT risk_weight
FROM instruments i
JOIN categories c
ON 
i.category_id = c.id
WHERE i.id = %s
"""

CHECK_CATEGORY = """
SELECT id
FROM categories
WHERE id = %s;
"""

CHECK_INSTRUMENT_BY_SYMBOL = """
SELECT id
FROM instruments
WHERE symbol = %s;
"""

GET_INSTRUMENTS = """
SELECT
    i.id,
    i.symbol,
    i.name,
    i.category_id,
    c.name AS category,
    i.current_price,
    i.is_active,
    i.created_at,
    i.updated_at
FROM instruments i
JOIN categories c
    ON i.category_id = c.id
WHERE (%s IS NULL OR i.is_active = %s)
ORDER BY i.created_at DESC
LIMIT %s OFFSET %s;
"""

GET_INSTRUMENT_BY_ID = """
SELECT
    i.id,
    i.symbol,
    i.name,
    i.category_id,
    c.name AS category,
    i.current_price,
    i.is_active,
    i.created_at,
    i.updated_at
FROM instruments i
JOIN categories c
    ON i.category_id = c.id
WHERE i.id = %s;
"""

ADD_INSTRUMENT = """
INSERT INTO instruments (
    symbol,
    name,
    category_id,
    current_price
) VALUES ( %s, %s, %s, %s );
"""

UPDATE_INSTRUMENT = """
UPDATE instruments
SET
    symbol = %s,
    name = %s,
    category_id = %s,
    current_price = %s,
    is_active = %s
WHERE id = %s;
"""

DELETE_INSTRUMENT = """
UPDATE instruments
SET is_active = FALSE
WHERE id = %s;
"""

GROUP_USER_INSTRUMENT = """
SELECT

i.id,
i.symbol,
i.name,
c.name as "category",
c.risk_weight,
i.current_price,

SUM(
CASE
WHEN t.type='BUY'
THEN t.quantity
ELSE 0
END
) total_buy,

SUM(
CASE
WHEN t.type='SELL'
THEN t.quantity
ELSE 0
END
) total_sell

FROM transactions t

JOIN instruments i
ON
i.id = t.instrument_id

JOIN categories c
ON 
i.category_id = c.id

WHERE
t.user_id=%s

GROUP BY
i.id;
"""
