# ============================
# WRITE
# ============================

INSERT_PLAN = """
INSERT INTO plans (
    title,
    min_amount,
    duration,
    roi,
    risk_management,
    description,
    status
)
VALUES (
    %s,
    %s,
    %s,
    %s,
    %s,
    %s,
    'ACTIVE'
);
"""

INSERT_PLAN_FEATURE = """
INSERT INTO plan_features (
    plan_id,
    feature
)
VALUES (
    %s,
    %s
);
"""

UPDATE_PLAN = """
UPDATE plans
SET
    title = %s,
    min_amount = %s,
    duration = %s,
    roi = %s,
    risk_management = %s,
    description = %s
WHERE id = %s;
"""

ACTIVATE_PLAN = """
UPDATE plans
SET status = 'ACTIVE'
WHERE id = %s;
"""

DEACTIVATE_PLAN = """
UPDATE plans
SET status = 'INACTIVE'
WHERE id = %s;
"""

UPDATE_PLAN_FEATURE = """
UPDATE plan_features
SET feature = %s
WHERE id = %s;
"""

DELETE_PLAN_FEATURE = """
DELETE
FROM plan_features
WHERE id = %s;
"""

DELETE_PLAN = """
DELETE p
FROM plans p
WHERE p.id = %s
AND NOT EXISTS (
    SELECT 1
    FROM subscriptions s
    WHERE s.plan_id = p.id
);
"""
# ============================
# Read
# ============================

GET_PLAN = """
SELECT *
FROM plans
WHERE id = %s;
"""

GET_PLANS = """
SELECT *
FROM plans
ORDER BY created_at DESC;
"""

GET_PLAN_FEATURES = """
SELECT *
FROM plan_features
WHERE plan_id = %s
ORDER BY id;
"""

CHECK_USER_ACTIVE_PLAN = """
SELECT *
FROM subscriptions
WHERE user_id = %s
AND plan_id = %s
AND status = 'ACTIVE';
"""

# ============================
# VALIDATION QUERIES
# ============================


GET_PLAN_FEATURE = """
SELECT *
FROM plan_features
WHERE id = %s;
"""

GET_PLAN_FEATURE_BY_NAME = """
SELECT *
FROM plan_features
WHERE plan_id = %s
AND feature = %s;
"""

GET_ACTIVE_PLAN_BY_ID = """
SELECT *
FROM plans
WHERE id = %s
AND status = 'ACTIVE';
"""

GET_PLAN_BY_TITLE = """
SELECT *
FROM plans
WHERE title = %s
"""
