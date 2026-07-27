CREATE TABLE IF NOT EXISTS user_addresses (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    
    city VARCHAR(255) NOT NULL,
    state VARCHAR(255) NOT NULL,
    
    zip VARCHAR(255) NOT NULL,
	address1 VARCHAR(255) NOT NULL,
    address2 VARCHAR(255),
     
	FOREIGN KEY (user_id)
    REFERENCES users(id)
    ON DELETE CASCADE
    ) ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COLLATE=utf8mb4_0900_ai_ci;