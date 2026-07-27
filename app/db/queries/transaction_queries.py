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
