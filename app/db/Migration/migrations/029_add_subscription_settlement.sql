ALTER TABLE subscriptions
    ADD COLUMN settled_amount DECIMAL(20,8) NULL,
    ADD COLUMN settled_at TIMESTAMP NULL;
