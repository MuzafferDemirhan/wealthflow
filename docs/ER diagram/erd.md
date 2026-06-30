erDiagram
    %% Relationships
    USER ||--o{ ACCOUNT : "has"
    USER ||--o{ BUDGET : "sets"
    USER ||--o{ HOLDING : "owns"
    ACCOUNT ||--o{ TRANSACTION : "contains"
    CATEGORY ||--o{ TRANSACTION : "categorizes"
    CATEGORY ||--o{ BUDGET : "allocates to"

    %% Entities
    USER {
        UNIQUEIDENTIFIER id PK
        VARCHAR(255) email "NOT NULL, UNIQUE"
        VARCHAR(255) hashed_pw
        VARCHAR(255) full_name
        BIT is_active "DEFAULT 1"
        BIT is_admin "DEFAULT 0"
        DATETIME2 created_at
        DATETIME2 updated_at
    }

    CATEGORY {
        UNIQUEIDENTIFIER id PK
        VARCHAR(100) name "NOT NULL"
        VARCHAR(50) icon
        VARCHAR(7) color
        BIT is_default "DEFAULT 0"
    }

    ACCOUNT {
        UNIQUEIDENTIFIER id PK
        UNIQUEIDENTIFIER user_id FK "ON DELETE CASCADE"
        VARCHAR(50) provider "NOT NULL"
        VARCHAR(255) external_id "NOT NULL"
        VARCHAR(255) institution
        VARCHAR(50) account_type
        DECIMAL(15_2) balance
        VARCHAR(3) currency "DEFAULT 'PLN'"
        DATETIME2 last_synced_at
        DATETIME2 created_at
    }

    TRANSACTION {
        UNIQUEIDENTIFIER id PK
        UNIQUEIDENTIFIER account_id FK "ON DELETE CASCADE"
        UNIQUEIDENTIFIER category_id FK
        VARCHAR(255) external_id "UNIQUE"
        DECIMAL(15_2) amount "NOT NULL"
        VARCHAR(3) currency "DEFAULT 'PLN'"
        VARCHAR(MAX) description
        BIT is_manual "DEFAULT 0"
        DATE date "NOT NULL"
        DATETIME2 created_at
    }

    BUDGET {
        UNIQUEIDENTIFIER id PK
        UNIQUEIDENTIFIER user_id FK "ON DELETE CASCADE"
        UNIQUEIDENTIFIER category_id FK
        DECIMAL(15_2) amount "NOT NULL"
        VARCHAR(20) period "DEFAULT 'monthly'"
        DATETIME2 created_at
    }

    HOLDING {
        UNIQUEIDENTIFIER id PK
        UNIQUEIDENTIFIER user_id FK "ON DELETE CASCADE"
        VARCHAR(20) ticker "NOT NULL"
        DECIMAL(15_6) shares "NOT NULL"
        DECIMAL(15_2) avg_cost "NOT NULL"
        VARCHAR(20) asset_type
        DATETIME2 created_at
    }