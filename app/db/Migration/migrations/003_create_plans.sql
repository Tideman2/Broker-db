CREATE TABLE IF NOT EXISTS plans (
    id INT PRIMARY KEY AUTO_INCREMENT,

    title VARCHAR(100) NOT NULL,

    min_amount DECIMAL(20,8) NOT NULL,

    duration INT NOT NULL COMMENT 'Duration in days',

    roi DECIMAL(5,2) NOT NULL COMMENT 'Expected ROI (%)',

    risk_management ENUM(
        'STANDARD',
        'ADVANCED_HEDGING',
        'TAILORED_MULTI_LAYER'
    ) NOT NULL,

    status ENUM(
        'ACTIVE',
        'INACTIVE'
    ) NOT NULL DEFAULT 'ACTIVE',

    description TEXT,

    created_at TIMESTAMP
        DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP
        DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP
)
ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COLLATE=utf8mb4_0900_ai_ci;