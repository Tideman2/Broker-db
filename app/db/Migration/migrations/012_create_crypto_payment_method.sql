CREATE TABLE IF NOT EXISTS crypto_payment_method (
    id INT PRIMARY KEY AUTO_INCREMENT,
    payment_method_id INT NOT NULL UNIQUE,

    created_at TIMESTAMP
        DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (payment_method_id)
        REFERENCES payment_methods(id)
        ON DELETE CASCADE
        
)  ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COLLATE=utf8mb4_0900_ai_ci; 