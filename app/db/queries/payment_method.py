GET_PAYMENT_METHOD = """
SELECT *
FROM payment_methods pm
WHERE pm.id = %s
"""

GET_PAYMENT_METHODS = """
SELECT *
FROM payment_methods
ORDER BY id
"""

GET_CRYPTO_PAYMENT_METHOD = """
SELECT *
FROM payment_methods pm
JOIN crypto_payment_method cpm
    ON pm.id = cpm.payment_method_id
WHERE pm.id = %s
"""

GET_BANK_PAYMENT_METHOD = """
SELECT *
FROM payment_methods pm
JOIN bank_payment_methods bpm
    ON pm.id = bpm.payment_method_id
WHERE pm.id = %s
"""

GET_BANK_PAYMENT_METHODS = """
SELECT *
FROM payment_methods pm
JOIN bank_payment_methods bpm
    ON pm.id = bpm.payment_method_id
ORDER BY bpm.bank_name
"""

UPDATE_BANK_PAYMENT_METHOD = """
UPDATE bank_payment_methods
SET
    bank_name = %s,
    account_name = %s,
    account_number = %s
WHERE id = %s
"""

ADD_BANK_PAYMENT_METHOD = """
INSERT INTO bank_payment_methods (
    bank_name,
    account_name,
    account_number
) VALUES ( %s, %s, %s );
"""

DELETE_BANK_PAYMENT_METHOD = """
DELETE FROM bank_payment_methods
WHERE id = %s
"""
