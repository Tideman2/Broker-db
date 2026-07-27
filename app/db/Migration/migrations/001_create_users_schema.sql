CREATE TABLE IF NOT EXISTS users (
    id INT NOT NULL AUTO_INCREMENT,
    
    email VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    
    dob DATE DEFAULT NULL,
    username VARCHAR(255) DEFAULT NULL,
    
    accept_terms BOOLEAN NOT NULL,
    marketing_opt_in BOOLEAN NOT NULL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
    DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP,
    
    password_hash VARCHAR(256) NOT NULL,

    PRIMARY KEY (id),

    UNIQUE KEY email (email),
    UNIQUE KEY phone (phone),
    UNIQUE KEY username (username)

) ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COLLATE=utf8mb4_0900_ai_ci;

