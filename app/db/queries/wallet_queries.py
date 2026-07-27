
INSERT_WALLET = """
INSERT INTO wallet (
    user_id,
    available,
    locked
) VALUES (
    %s,
    0,
    0
)
"""

GET_WALLET = """
SELECT *
FROM wallet
WHERE user_id = %s
"""

CREDIT_AVAILABLE_BALANCE = """
UPDATE wallet
SET
    available = available + %s
WHERE user_id = %s
"""

DEBIT_AVAILABLE_BALANCE = """
UPDATE wallet
SET
    available = available - %s
WHERE user_id = %s
AND available >= %s
"""

LOCK_FUNDS = """
UPDATE wallet
SET
    available = available - %s,
    locked = locked + %s
WHERE user_id = %s
"""

UNLOCK_FUNDS = """
UPDATE wallet
SET
    available = available + %s,
    locked = locked - %s
WHERE user_id = %s
"""

CONSUME_LOCKED_FUNDS = """
UPDATE wallet
SET
    locked = locked - %s
WHERE user_id = %s
"""
