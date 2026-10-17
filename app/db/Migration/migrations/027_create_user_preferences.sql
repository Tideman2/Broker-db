CREATE TABLE IF NOT EXISTS user_preferences (
    user_id INT NOT NULL,

    currency_display ENUM(
        'usd',
        'eur',
        'gbp'
    ) NOT NULL DEFAULT 'usd',

    created_at TIMESTAMP
        DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
        DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (user_id),

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE

) ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COLLATE=utf8mb4_0900_ai_ci;
