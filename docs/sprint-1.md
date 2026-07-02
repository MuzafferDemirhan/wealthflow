# Sprint 1 — Backend Core (Auth, Accounts, Categories, Budgets, Transactions)

## Goal
Deliver the backend business logic and API endpoints for core personal finance features.

## Deliverables

### Authentication (`/api/v1/auth`)
- **Register** (`POST /register`) — email, password validation, duplicate detection
- **Login** (`POST /login`) — returns access + refresh token pair
- **Me** (`GET /me`) — authenticated user profile
- **Refresh** (`POST /refresh`) — rotate refresh token (reuse detection)
- **Logout** (`POST /logout`) — revoke refresh token
- Password hashing via **passlib** + **bcrypt**

### Categories (`/api/v1/categories`)
- `GET /categories` — list all system categories
- `GET /categories/{slug}` — get by slug
- Idempotent seeding of 12 system categories at startup (income, housing, groceries, dining, transport, utilities, healthcare, entertainment, shopping, education, transfers, other)

### Accounts (`/api/v1/accounts`)
- `GET /accounts` — list user accounts (scoped to current user)
- `GET /accounts/{id}` — single account
- `DELETE /accounts/{id}` — deactivate (soft-delete via `is_active`)
- `POST /accounts/{id}/sync` — trigger Celery transaction sync

### Budgets (`/api/v1/budgets`)
- `POST /budgets` — create (unique per user + category + month)
- `GET /budgets` — list with computed spending, remaining, progress %
- `PUT /budgets/{id}` — update limit/category
- `DELETE /budgets/{id}` — delete
- Spending calculation per category per month

### Transactions (`/api/v1/transactions`)
- `GET /transactions` — list with filters (account, category, date range, status, search)
- `GET /transactions/{id}` — single transaction
- `PATCH /transactions/{id}/category` — override category (user-sourced)
- `POST /transactions/manual` — create manual transaction
- Pagination support (limit + offset)

### Data Model Enhancements
- `dedupe_hash` column on Transaction (SHA-256 of normalized fields, unique per account)
- `category_source` and `category_confidence` columns for ML tracking
- Auth token blacklisting via RefreshToken table
- `is_active` soft-delete on Account

### Testing
- 16 auth tests (register, login, me, refresh, logout edge cases)
- 10 account tests (CRUD, ownership, sync trigger)
- 15 category tests (seeding, idempotency, API)
- 15 budget tests (CRUD, spending computation, API)
- 20 transaction tests (CRUD, filtering, pagination, category update)
- Pre-existing `test_auth.py` failures (passlib/bcrypt compat) — not caused by Sprint 1

## Key Decisions
- **Soft-delete** for accounts (is_active flag) rather than hard delete
- **Unique constraint** on (user_id, category_id, period_month) for budgets
- **`dedupe_hash`** computed from (account_id, amount, currency, booking_date, description) — normalized whitespace/case, deterministic
- **Pydantic v2** with `from_attributes=True` throughout
- Auth tokens expire: 30 min (access), 7 days (refresh)
- Refresh token rotation with old-token blacklisting
