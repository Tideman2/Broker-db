UPDATE subscriptions s
LEFT JOIN (
    SELECT
        subscription_id,
        SUM(CASE WHEN type = 'BUY' THEN quantity * price ELSE 0 END) AS buys,
        SUM(CASE WHEN type = 'SELL' THEN quantity * price ELSE 0 END) AS sells
    FROM transactions
    WHERE subscription_id IS NOT NULL
    GROUP BY subscription_id
) t ON t.subscription_id = s.id
SET
    s.settled_amount =
        s.invested_amount - COALESCE(t.buys, 0) + COALESCE(t.sells, 0),
    s.settled_at = s.updated_at
WHERE s.status IN ('COMPLETED', 'CANCELLED')
AND s.settled_amount IS NULL;
