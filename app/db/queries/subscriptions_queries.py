# ============================
# WRITE
# ============================

INSERT_SUBSCRIPTION = """
INSERT INTO subscriptions (
    user_id,
    plan_id,
    invested_amount,
    expiration_date,
    pool,
    status
)
VALUES (
    %s,
    %s,
    %s,
    %s,
    %s,
    'ACTIVE'
);
"""

FAIL_SUBSCRIPTION = """
UPDATE subscriptions
SET status = 'FAILED'
WHERE id = %s
AND status = 'PENDING';
"""

COMPLETE_SUBSCRIPTION = """
UPDATE subscriptions
SET status = 'COMPLETED'
WHERE id = %s
AND status = 'ACTIVE';
"""

CANCEL_SUBSCRIPTION = """
UPDATE subscriptions
SET status = 'CANCELLED'
WHERE id = %s
AND status = 'ACTIVE';
"""

# ============================
# Read
# ============================

GET_SUBSCRIPTION = """
SELECT
    s.*,

    p.title,
    p.roi,
    p.min_amount,
    p.duration,
    p.risk_management,
    p.description

FROM subscriptions s

JOIN plans p
ON s.plan_id = p.id

WHERE s.id = %s;
"""

GET_USER_SUBSCRIPTIONS = """
SELECT
    s.*,

    p.title,
    p.roi,
    p.duration

FROM subscriptions s

JOIN plans p
ON s.plan_id = p.id

WHERE s.user_id = %s

ORDER BY s.created_at DESC;
"""

GET_ACTIVE_SUBSCRIPTION = """
SELECT *
FROM subscriptions
WHERE id = %s 
AND user_id = %s
AND status = 'ACTIVE';
"""

GET_ACTIVE_SUBSCRIPTIONS_BY_USER = """
SELECT *
FROM subscriptions
WHERE user_id = %s
AND status = 'ACTIVE'
ORDER BY created_at DESC;
"""

# ============================
# POOL
# ============================

DEBIT_SUBSCRIPTION_POOL = """
UPDATE subscriptions
SET pool = pool - %s
WHERE id = %s
AND pool >= %s
"""

CREDIT_SUBSCRIPTION_POOL = """
UPDATE subscriptions
SET pool = pool + %s
WHERE id = %s
"""

ZERO_SUBSCRIPTION_POOL = """
UPDATE subscriptions
SET pool = 0
WHERE id = %s
"""

RECORD_SUBSCRIPTION_SETTLEMENT = """
UPDATE subscriptions
SET
    settled_amount = %s,
    settled_at = %s
WHERE id = %s
AND settled_at IS NULL
"""

GET_SUBSCRIPTION_TRANSACTIONS = """
SELECT
    instrument_id,
    type,
    quantity,
    price,
    executed_at
FROM transactions
WHERE subscription_id = %s
ORDER BY executed_at, id
"""

GET_SUBSCRIPTION_INSTRUMENT_TRANSACTIONS = """
SELECT
    instrument_id,
    type,
    quantity,
    price,
    executed_at
FROM transactions
WHERE subscription_id = %s
AND instrument_id = %s
ORDER BY executed_at, id
"""

GET_SUBSCRIPTION_HOLDINGS = """
SELECT
    i.id AS instrument_id,
    i.symbol,
    i.name,
    c.name AS category,
    i.current_price,
    i.is_active,
    COALESCE(SUM(CASE WHEN t.type = 'BUY' THEN t.quantity ELSE 0 END), 0) AS total_buy,
    COALESCE(SUM(CASE WHEN t.type = 'SELL' THEN t.quantity ELSE 0 END), 0) AS total_sell
FROM transactions t
JOIN instruments i ON i.id = t.instrument_id
JOIN categories c ON c.id = i.category_id
WHERE t.subscription_id = %s
GROUP BY i.id, i.symbol, i.name, c.name, i.current_price, i.is_active
ORDER BY i.symbol
"""

GET_DUE_SUBSCRIPTIONS = """
SELECT *
FROM subscriptions
WHERE status = 'ACTIVE'
AND expiration_date <= NOW()
"""

# ============================
# VALIDATION QUERIES
# ============================

GET_SUBSCRIPTION_BY_ID = """
SELECT *
FROM subscriptions
WHERE id = %s;
"""

GET_ACTIVE_SUBSCRIPTION_BY_USER_AND_PLAN = """
SELECT *
FROM subscriptions
WHERE user_id = %s
AND plan_id = %s
AND status = 'ACTIVE'
"""
