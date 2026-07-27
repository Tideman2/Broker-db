-- Seed assets

INSERT INTO assets (
    symbol,
    name,
    address,
    is_active
)
VALUES
    ('ETH', 'Ethereum', NULL, TRUE),
    ('BNB', 'BNB', NULL, TRUE),
    ('USDT', 'Tether USD', '0x55d398326f99059fF775485246999027B3197955', TRUE),
    ('USDC', 'USD Coin', '0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d', TRUE),
    ('BUSD', 'Binance USD', '0xe9e7cea3dedca5984780bafc599bd69add087d56', FALSE);