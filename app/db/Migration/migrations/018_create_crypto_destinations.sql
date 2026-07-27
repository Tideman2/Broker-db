CREATE TABLE IF NOT EXISTS crypto_destinations (
    id INT PRIMARY KEY AUTO_INCREMENT,
    withdrawal_destinations_id INT NOT NULL,
    asset_id INT NOT NULL,
    address VARCHAR(255) NOT NULL UNIQUE,

    created_at TIMESTAMP
        DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (withdrawal_destinations_id)
        REFERENCES withdrawal_destination(id)
        ON DELETE CASCADE

        FOREIGN KEY (asset_id)
        REFERENCES assets(id)
        ON DELETE CASCADE
        
)  ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COLLATE=utf8mb4_0900_ai_ci; 