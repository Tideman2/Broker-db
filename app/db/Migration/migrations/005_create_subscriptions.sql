CREATE TABLE IF NOT EXISTS subscriptions (
    id INT PRIMARY KEY AUTO_INCREMENT,

    user_id INT NOT NULL,

    plan_id INT NOT NULL,

    invested_amount DECIMAL(20,8) NOT NULL,

    expiration_date TIMESTAMP NOT NULL,

    status ENUM(
        'PENDING',
        'ACTIVE',
        'CANCELLED',
        'COMPLETED',
        'FAILED'
    ) NOT NULL DEFAULT 'PENDING',

    created_at TIMESTAMP
        DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP
        DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    cancelled_at TIMESTAMP NULL,
    failure_reason VARCHAR(255) NULL,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    FOREIGN KEY (plan_id)
        REFERENCES plans(id)
        ON DELETE CASCADE
)
ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COLLATE=utf8mb4_0900_ai_ci;