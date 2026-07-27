ADD_DEPOSIT = """
INSERT INTO deposits (
    user_id,
    amount,
    asset_id,
    status,
    payment_method_id
) VALUES ( %s, %s, %s, "pending", %s );
"""

CONFIRM_DEPOSIT = """
UPDATE deposits
SET 
    status = 'confirmed',
    confirmed_at = %s
WHERE id = %s
AND user_id = %s
AND status = 'pending';
"""

REJECT_DEPOSIT = """
UPDATE deposits
SET status = 'rejected'
WHERE id = %s
AND user_id = %s
AND status = 'pending';
"""

GET_DEPOSITS = """
SELECT *
FROM deposits
ORDER BY created_at DESC;
"""

GET_DEPOSIT = """
SELECT
    d.id,
    d.amount,
    d.status,
    d.confirmed_at,
    d.created_at,

    a.id AS asset_id,
    a.symbol AS asset_symbol,
    a.name AS asset_name,
    a.address AS asset_address,

    pm.id AS payment_method_id,
    pm.name AS payment_method_name,
    pm.type AS payment_method_type,

    cpm.id AS crypto_payment_method_id,

    bpm.id AS bank_payment_method_id,
    bpm.bank_name,
    bpm.account_name,
    bpm.account_number

FROM deposits d

JOIN assets a
    ON d.asset_id = a.id

JOIN payment_methods pm
    ON d.payment_method_id = pm.id

LEFT JOIN crypto_payment_method cpm
    ON pm.id = cpm.payment_method_id

LEFT JOIN bank_payment_methods bpm
    ON pm.id = bpm.payment_method_id

WHERE d.id = %s;
"""

GET_RECENT_DEPOSITS = """
SELECT
    d.id,
    d.amount,
    d.status,
    d.created_at,

    a.id AS asset_id,
    a.symbol,
    a.name,

    pm.id AS payment_method_id,
    pm.type AS payment_method_type,

    cpm.network,
    cpm.wallet_address,

    bpm.bank_name,
    bpm.account_name,
    bpm.account_number

FROM deposits d

JOIN assets a
    ON d.asset_id = a.id

JOIN payment_methods pm
    ON d.payment_method_id = pm.id

LEFT JOIN crypto_payment_method cpm
    ON pm.id = cpm.payment_method_id

LEFT JOIN bank_payment_methods bpm
    ON pm.id = bpm.payment_method_id

WHERE d.user_id = %s

ORDER BY d.created_at DESC

LIMIT %s OFFSET %s;
"""
