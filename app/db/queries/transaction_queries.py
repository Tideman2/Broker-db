INSERT_BUY_TRANSACTION = """
INSERT INTO transactions ( user_id, instrument_id, type, quantity, price )
VALUES ( %s, %s, 'BUY', %s, %s )
"""

INSERT_SELL_TRANSACTION = """
INSERT INTO transactions ( user_id, instrument_id, type, quantity, price )
VALUES ( %s, %s, 'SELL', %s, %s )
"""

GET_TRANSACTIONS_RELATED_TO_A_USER = """
SELECT *
FROM transactions tr
JOIN instruments ints
ON tr.instrument_id = ints.id
WHERE tr.user_id = %s;
"""

# ============================
# Read
# ============================

# Columns are listed explicitly and aliased. A SELECT * across this
# join would collide on id, created_at and updated_at, and the
# instrument's values overwrite the transaction's.
#
# Each optional filter is passed twice and guarded with IS NULL so a
# single static query covers every filter combination.
GET_TRADES = """
SELECT
    tr.id AS transaction_id,
    tr.instrument_id,
    tr.type,
    tr.quantity,
    tr.price,
    tr.executed_at,

    i.symbol,
    i.name

FROM transactions tr

JOIN instruments i
ON tr.instrument_id = i.id

WHERE tr.user_id = %s

AND (
    %s IS NULL
    OR tr.instrument_id = %s
)

AND (
    %s IS NULL
    OR tr.type = %s
)

AND (
    %s IS NULL
    OR tr.executed_at >= NOW() - INTERVAL %s DAY
)

ORDER BY tr.executed_at DESC

LIMIT %s OFFSET %s;
"""
