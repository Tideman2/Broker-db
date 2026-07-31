CREATE TABLE IF NOT EXISTS withdrawal_destination (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,

    label VARCHAR(50) NOT NULL,
    
    type ENUM(
        'CRYPTO',
        'BANK'
    ) NOT NULL,

    created_at TIMESTAMP
        DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,
        
    UNIQUE KEY uk_user_label (user_id, label)

) ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COLLATE=utf8mb4_0900_ai_ci;