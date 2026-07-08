erDiagram

    %% ── Core user & auth ───────────────────────────────────────────────────
    USER_ACCOUNT {
        UNIQUEIDENTIFIER id PK
        NVARCHAR_255 email "UNIQUE NOT NULL"
        NVARCHAR_255 hashed_password "NOT NULL"
        NVARCHAR_255 full_name "NOT NULL"
        NVARCHAR_20  role "user | admin  DEFAULT user"
        BIT          is_active "DEFAULT 1"
        BIT          is_verified "DEFAULT 0"
        DATETIME2    created_at "NOT NULL"
        DATETIME2    updated_at "NOT NULL"
    }

    REFRESH_TOKEN {
        UNIQUEIDENTIFIER id PK
        UNIQUEIDENTIFIER user_id FK
        NVARCHAR_255 token_hash "UNIQUE NOT NULL"
        DATETIME2    expires_at "NOT NULL"
        BIT          revoked "DEFAULT 0"
        DATETIME2    created_at
        DATETIME2    updated_at
    }

    %% ── Open Banking ───────────────────────────────────────────────────────
    BANK_CONNECTION {
        UNIQUEIDENTIFIER id PK
        UNIQUEIDENTIFIER user_id FK
        NVARCHAR_20  provider "plaid"
        NVARCHAR_100 institution_id "NOT NULL"
        NVARCHAR_255 institution_name "NOT NULL"
        NVARCHAR_255 external_reference "UNIQUE NOT NULL"
        NVARCHAR_20  status "pending|linked|expired|revoked|error"
        DATE         consent_expires_at
        DATETIME2    last_synced_at
        DATETIME2    created_at
        DATETIME2    updated_at
    }

    ACCOUNT {
        UNIQUEIDENTIFIER id PK
        UNIQUEIDENTIFIER user_id FK "denormalised owner"
        UNIQUEIDENTIFIER bank_connection_id FK
        NVARCHAR_255 external_account_id "UNIQUE NOT NULL"
        NVARCHAR_255 display_name "NOT NULL"
        NVARCHAR_20  account_type "checking|savings|credit_card|loan|investment|other"
        NVARCHAR_34  iban
        NVARCHAR_3   currency "NOT NULL"
        NUMERIC_19_4 current_balance "DEFAULT 0"
        DATETIME2    balance_as_of
        BIT          is_active "DEFAULT 1"
        DATETIME2    created_at
        DATETIME2    updated_at
    }

    %% ── Transactions & categorisation ──────────────────────────────────────
    TRANSACTION {
        UNIQUEIDENTIFIER id PK
        UNIQUEIDENTIFIER account_id FK
        UNIQUEIDENTIFIER category_id FK "nullable"
        NVARCHAR_255 external_id "nullable, INDEX"
        NVARCHAR_64  dedupe_hash "NOT NULL — UNIQUE per account_id"
        NUMERIC_19_4 amount "NOT NULL  neg=outflow  pos=inflow"
        NVARCHAR_3   currency "NOT NULL"
        DATE         booking_date "NOT NULL, INDEX"
        DATE         value_date "nullable"
        NVARCHAR_20  status "pending | booked"
        NVARCHAR_500 description "DEFAULT empty"
        NVARCHAR_255 counterparty_name "nullable"
        NVARCHAR_10  category_source "ml | rule | user"
        FLOAT        category_confidence "ML prob score 0-1"
        JSON         raw_payload "full provider payload"
        DATETIME2    created_at
        DATETIME2    updated_at
    }

    CATEGORY {
        UNIQUEIDENTIFIER id PK
        UNIQUEIDENTIFIER parent_id FK "self-ref nullable"
        UNIQUEIDENTIFIER user_id FK "NULL for system categories"
        NVARCHAR_100 name "NOT NULL"
        NVARCHAR_100 slug "UNIQUE NOT NULL"
        NVARCHAR_50  icon "nullable"
        BIT          is_system "DEFAULT 0 — system rows not user-editable"
        DATETIME2    created_at
        DATETIME2    updated_at
    }

    %% ── Budgets ────────────────────────────────────────────────────────────
    BUDGET {
        UNIQUEIDENTIFIER id PK
        UNIQUEIDENTIFIER user_id FK
        UNIQUEIDENTIFIER category_id FK "nullable — NULL = overall budget"
        DATE         period_month "NOT NULL always 1st of month"
        NUMERIC_19_4 amount_limit "NOT NULL"
        NVARCHAR_3   currency "NOT NULL"
        DATETIME2    created_at
        DATETIME2    updated_at
    }

    %% ── Portfolio ──────────────────────────────────────────────────────────
    HOLDING {
        UNIQUEIDENTIFIER id PK
        UNIQUEIDENTIFIER user_id FK
        UNIQUEIDENTIFIER account_id FK "nullable"
        NVARCHAR_20  symbol "NOT NULL, INDEX"
        NVARCHAR_255 name "NOT NULL"
        NVARCHAR_20  asset_type "stock|etf|mutual_fund|bond|crypto|cash|other"
        NVARCHAR_3   currency "NOT NULL"
        NUMERIC_19_8 quantity "NOT NULL"
        NUMERIC_19_4 cost_basis "nullable"
        NUMERIC_19_6 current_price "nullable"
        DATE         as_of_date "nullable"
        NVARCHAR_1000 notes "nullable"
        DATETIME2    created_at
        DATETIME2    updated_at
    }

    %% ── Notifications ──────────────────────────────────────────────────────
    NOTIFICATION {
        UNIQUEIDENTIFIER id PK
        UNIQUEIDENTIFIER user_id FK
        NVARCHAR_50  type "budget_alert|sync_complete|report_ready"
        NVARCHAR_255 title "NOT NULL"
        TEXT         body "nullable"
        JSON         payload "nullable"
        BIT          is_read "DEFAULT 0"
        DATETIME2    created_at
        DATETIME2    updated_at
    }

    %% ── AI Chat ────────────────────────────────────────────────────────────
    CHAT_MESSAGE {
        UNIQUEIDENTIFIER id PK
        UNIQUEIDENTIFIER user_id FK
        UNIQUEIDENTIFIER conversation_id "groups messages into sessions"
        NVARCHAR_20  role "user | assistant"
        TEXT         content "NOT NULL"
        DATETIME2    created_at
        DATETIME2    updated_at
    }

    %% ── Exports ────────────────────────────────────────────────────────────
    EXPORT {
        UNIQUEIDENTIFIER id PK
        UNIQUEIDENTIFIER user_id FK
        NVARCHAR_10  format "pdf | csv"
        NVARCHAR_50  report_type "category_breakdown|income_vs_expenses|monthly_trends|net_worth"
        NVARCHAR_20  status "processing|completed|failed"
        NVARCHAR_255 filename "nullable"
        NVARCHAR_512 file_path "nullable"
        JSON         params "nullable — report generation parameters"
        TEXT         error_message "nullable"
        DATETIME2    created_at
        DATETIME2    updated_at
    }

    %% ── Relationships ──────────────────────────────────────────────────────

    %% User → auth
    USER_ACCOUNT ||--o{ REFRESH_TOKEN : "has (CASCADE)"

    %% User → bank connections → accounts → transactions
    USER_ACCOUNT ||--o{ BANK_CONNECTION : "owns (CASCADE)"
    BANK_CONNECTION ||--o{ ACCOUNT : "exposes (CASCADE)"
    ACCOUNT ||--o{ TRANSACTION : "contains (CASCADE)"

    %% Denormalised owner on account (NO ACTION — avoids multi-cascade-path)
    USER_ACCOUNT ||--o{ ACCOUNT : "denorm owner (NO ACTION)"

    %% Category taxonomy (self-referential + user custom)
    CATEGORY ||--o{ CATEGORY : "parent → children (NO ACTION)"
    USER_ACCOUNT ||--o{ CATEGORY : "custom categories (CASCADE)"

    %% Category applied to transactions and budgets (NO ACTION — service layer enforces)
    CATEGORY ||--o{ TRANSACTION : "categorises (NO ACTION)"
    CATEGORY ||--o{ BUDGET : "scopes (NO ACTION)"

    %% User → budgets
    USER_ACCOUNT ||--o{ BUDGET : "sets (CASCADE)"

    %% User → portfolio
    USER_ACCOUNT ||--o{ HOLDING : "owns (CASCADE)"
    ACCOUNT |o--o{ HOLDING : "linked account (nullable)"

    %% User → notifications, chat, exports
    USER_ACCOUNT ||--o{ NOTIFICATION : "receives (CASCADE)"
    USER_ACCOUNT ||--o{ CHAT_MESSAGE : "sends (CASCADE)"
    USER_ACCOUNT ||--o{ EXPORT : "generates (CASCADE)"
