
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

# ============================
# MONEY FLOW
# ============================

GET_LATEST_MONEY_IN = """
SELECT
    id,
    type,
    amount,
    asset_symbol,
    status,
    occurred_at
FROM (
    SELECT
        d.id AS id,
        'DEPOSIT' AS type,
        d.amount AS amount,
        a.symbol AS asset_symbol,
        d.status AS status,
        d.confirmed_at AS occurred_at
    FROM deposits d

    JOIN assets a
    ON a.id = d.asset_id

    WHERE d.user_id = %s
    AND d.status = 'confirmed'
    AND d.confirmed_at IS NOT NULL

    UNION ALL

    SELECT
        s.id,
        'SUBSCRIPTION_PAYOUT',
        s.settled_amount,
        NULL,
        s.status,
        s.settled_at
    FROM subscriptions s

    WHERE s.user_id = %s
    AND s.settled_amount IS NOT NULL
    AND s.settled_amount > 0
    AND s.settled_at IS NOT NULL
) flow

ORDER BY occurred_at DESC, id DESC
LIMIT 4
"""

GET_LATEST_MONEY_OUT = """
SELECT
    id,
    type,
    amount,
    asset_symbol,
    status,
    occurred_at
FROM (
    SELECT
        w.id AS id,
        'WITHDRAWAL' AS type,
        w.amount AS amount,
        a.symbol AS asset_symbol,
        w.status AS status,
        w.confirmed_at AS occurred_at
    FROM withdrawals w

    JOIN assets a
    ON a.id = w.asset_id

    WHERE w.user_id = %s
    AND w.status = 'confirmed'
    AND w.confirmed_at IS NOT NULL

    UNION ALL

    SELECT
        s.id,
        'SUBSCRIPTION_INVESTMENT',
        s.invested_amount,
        NULL,
        s.status,
        s.created_at
    FROM subscriptions s

    WHERE s.user_id = %s
) flow

ORDER BY occurred_at DESC, id DESC
LIMIT 4
"""
