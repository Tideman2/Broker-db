
CHECK_INSTRUMENT = """
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
