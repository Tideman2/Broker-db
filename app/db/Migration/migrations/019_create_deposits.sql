CREATE TABLE IF NOT EXISTS deposits (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    asset_id INT NOT NULL,
    payment_method_id INT NOT NULL,

    amount DECIMAL(20,8) NOT NULL,
    status ENUM(
      'pending',
      'confirmed',
      'rejected'
    ) NOT NULL,

    confirmed_at TIMESTAMP,
    created_at TIMESTAMP
        DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
        DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    FOREIGN KEY (payment_method_id)
        REFERENCES payment_methods(id)
        ON DELETE CASCADE,

    FOREIGN KEY (asset_id)
        REFERENCES assets(id)
        ON DELETE CASCADE
        
)  ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COLLATE=utf8mb4_0900_ai_ci; 