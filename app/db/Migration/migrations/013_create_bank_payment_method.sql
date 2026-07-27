CREATE TABLE IF NOT EXISTS bank_payment_methods (
    id INT PRIMARY KEY AUTO_INCREMENT,
    payment_method_id INT NOT NULL,

    bank_name VARCHAR(50) NOT NULL UNIQUE,
    account_name VARCHAR(50) NOT NULL,
    account_number VARCHAR(50) NOT NULL UNIQUE,


    created_at TIMESTAMP
        DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (payment_method_id)
        REFERENCES payment_methods(id)
        ON DELETE CASCADE
        
)  ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COLLATE=utf8mb4_0900_ai_ci; 