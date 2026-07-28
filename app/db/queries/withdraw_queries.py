# ============================
# WRITE
# ============================

INSERT_WITHDRAWAL_RECORD = """
INSERT INTO withdrawals (
   user_id,
   asset_id,
   withdrawal_destination_id,
   amount,
   status
) VALUES (
    %s,
    %s,
    %s,
    %s,
    "pending"
)
"""

INSERT_WITHDRAW_DESTINATION = """
INSERT INTO withdrawal_destination (
    user_id,
    label,
    type
) VALUES (
    %s,
    %s,
    %s
)
"""

INSERT_CRYPTO_DESTINATION = """
INSERT INTO crypto_destinations (
    withdrawal_destinations_id,
    asset_id,
    address
) VALUES (
    %s,
    %s,
    %s
)
"""

INSERT_BANK_DESTINATION = """
INSERT INTO bank_destinations (
    withdrawal_destinations_id,
    bank_name,
    account_name,
    account_number
) VALUES (
    %s,
    %s,
    %s,
    %s
)
"""

# ============================
# READ
# ============================

GET_ASSET_BY_SYMBOL = """
SELECT *
FROM assets
WHERE symbol = %s;
"""

GET_WITHDRAWAL_RECORD = """
SELECT
    w.id,
    w.amount,
    w.status,
    w.confirmed_at,
    w.created_at,

    a.id AS asset_id,
    a.symbol AS asset_symbol,
    a.name AS asset_name,

    wd.id AS destination_id,
    wd.label AS destination_label,
    wd.type AS destination_type,

    cd.address,

    bd.bank_name,
    bd.account_name,
    bd.account_number

FROM withdrawals w

JOIN assets a
    ON w.asset_id = a.id

JOIN withdrawal_destination wd
    ON w.withdrawal_destination_id = wd.id

LEFT JOIN crypto_destinations cd
    ON wd.id = cd.withdrawal_destinations_id

LEFT JOIN bank_destinations bd
    ON wd.id = bd.withdrawal_destinations_id

WHERE w.id = %s;
"""

GET_WITHDRAWAL_DESTINATION = """
SELECT
    wd.id,
    wd.user_id,
    wd.label,
    wd.type,
    wd.created_at,

    cd.address,

    bd.bank_name,
    bd.account_name,
    bd.account_number,

    a.id AS asset_id,
    a.name AS asset_name,
    a.symbol AS asset_symbol

FROM withdrawal_destination wd

LEFT JOIN crypto_destinations cd
    ON wd.id = cd.withdrawal_destinations_id

LEFT JOIN bank_destinations bd
    ON wd.id = bd.withdrawal_destinations_id

LEFT JOIN assets a
    ON cd.asset_id = a.id  

WHERE wd.id = %s;
"""

GET_CRYPTO_DESTINATIONS = """
SELECT
    wd.id,
    wd.label,
    wd.created_at,

    cd.address,

    a.id AS asset_id,
    a.name AS asset_name,
    a.symbol AS asset_symbol    

FROM withdrawal_destination wd

JOIN crypto_destinations cd
    ON wd.id = cd.withdrawal_destinations_id

JOIN assets a
    ON cd.asset_id = a.id  

WHERE wd.user_id = %s
AND wd.type = 'CRYPTO'

ORDER BY wd.created_at DESC;
"""

GET_BANK_DESTINATIONS = """
SELECT
    wd.id,
    wd.label,
    wd.created_at,

    bd.bank_name,
    bd.account_name,
    bd.account_number

FROM withdrawal_destination wd

JOIN bank_destinations bd
    ON wd.id = bd.withdrawal_destinations_id

WHERE wd.user_id = %s
AND wd.type = 'BANK'

ORDER BY wd.created_at DESC;
"""


# ============================
# UPDATE
# ============================

UPDATE_WITHDRAWAL_DESTINATION = """
UPDATE withdrawal_destination
SET
    label = %s
WHERE id = %s
AND user_id = %s;
"""

UPDATE_CRYPTO_DESTINATION = """
UPDATE crypto_destinations cd

JOIN withdrawal_destination wd
    ON cd.withdrawal_destinations_id = wd.id

SET
    cd.address = %s,
    cd.asset_id = %s

WHERE wd.id = %s
AND wd.user_id = %s;
"""

UPDATE_BANK_DESTINATION = """
UPDATE bank_destinations bd

JOIN withdrawal_destination wd
    ON bd.withdrawal_destinations_id = wd.id

SET
    bd.bank_name = %s,
    bd.account_name = %s,
    bd.account_number = %s

WHERE wd.id = %s
AND wd.user_id = %s;
"""

DELETE_WITHDRAWAL_DESTINATION = """
DELETE wd
FROM withdrawal_destination wd
WHERE wd.id = %s
AND wd.user_id = %s
AND NOT EXISTS (
    SELECT 1
    FROM withdrawals wr
    WHERE wr.withdrawal_destination_id = wd.id
      AND wr.status = 'pending'
);
"""
