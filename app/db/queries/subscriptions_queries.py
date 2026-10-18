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
AND status = "ACTIVE"
"""
