# Sprint 2 - Open Banking Integration, ML Classifier, Portfolio, Reports

## Goal
Deliver the transaction ingestion pipeline via GoCardless/Nordigen, ML-powered transaction categorization, portfolio tracking, financial reports, and a bank-connect endpoint.

## Deliverables

### 1. Provider Adapter Pattern (`app/services/providers/`)
- **`base.py`** - abstract `ProviderAdapter` class + `ProviderTransaction` dataclass
- **`nordigen.py`** - `NordigenAdapter` with:
  - Token lifecycle (obtain, refresh, expire with 60s safety margin)
  - `fetch_accounts(requisition_id)` - maps Nordigen accounts to `ProviderAccount`
  - `fetch_transactions(account_id, since)` - fetches booked + pending, maps to `ProviderTransaction`
  - `fetch_balances(account_id)` - prefers `interimAvailable` balance
  - Requisition CRUD (`create_requisition`, `get_requisition`)
  - `list_institutions(country)` - sorted institution listing
  - 401 auto-retry (refresh token + retry once)
- **35 tests** covering all adapter methods, edge cases, error handling, token expiry, data mapping

### 2. Transaction Ingestion Pipeline (`app/tasks/ingestion.py`)
- **`sync_account_transactions(account_id)`** - per-account Celery task:
  1. Load account + connection (eagerly)
  2. Build provider adapter
  3. Compute date range (90-day lookback from last_synced_at)
  4. Fetch raw transactions from provider
  5. Dedupe via `dedupe_hash` unique constraint
  6. Refresh balance from provider (non-fatal if fails)
  7. Update `last_synced_at`
  8. Enqueue classification for new transactions
- **`sync_all_due_connections()`** - periodic fan-out task (Celery Beat every 4h):
  - Queries LINKED connections with `last_synced_at > 4h` or never synced
  - Fans out to per-account sync tasks
  - Celery Beat schedule configured in `app/core/celery_app.py`
- **14 tests** covering date computation, dedup, happy path, edge cases

### 3. ML Transaction Classifier (`app/ml/`)
- **`seed_data.py`** - 120 labeled Polish transactions across 12 categories (rule-based ground truth)
- **`classifier.py`** - scikit-learn pipeline:
  - `char_wb` TF-IDF vectorizer (2-5 character n-grams)
  - `LogisticRegression(C=10.0)` with `CalibratedClassifierCV(sigmoid)`
  - Confidence threshold: 0.3 (below threshold returns "other")
  - Rule-based classification runs FIRST (keyword matching); ML only falls through for unmatched
  - Serialization support (dumps/loads)
  - `train_default()` - trains on seed data
  - `predict(description, counterparty_name, amount)` - rule + ML
- **30 tests** covering rules, ML, confidence, edge cases, serialization, DB integration

### 4. Classification Task (`app/tasks/classification.py`)
- **`classify_transaction(transaction_id)`** - Celery task:
  - Loads transaction, skips if user-categorized
  - Runs classifier → assigns category_id, source, confidence
- **`retrain_classifier()`** - resets and retrains the model

### 5. Portfolio (`/api/v1/portfolio`)
- **Data model**: `Holding` (symbol, name, asset_type, quantity, cost_basis, current_price, currency)
- **Endpoints**:
  - `GET /portfolio` - list user holdings
  - `GET /portfolio/{id}` - single holding
  - `POST /portfolio` - create
  - `PUT /portfolio/{id}` - update
  - `DELETE /portfolio/{id}` - delete
  - `GET /portfolio/summary` - compute market value, gain/loss, allocation %, account balances included
- **22 tests** covering CRUD, summary computation, ownership scoping

### 6. Reports (`/api/v1/reports`)
- **Report functions** (`app/services/report_service.py`):
  - `get_category_breakdown` - spending by category with optional account filter
  - `get_income_vs_expenses` - totals or monthly breakdown
  - `get_monthly_trends` - last N months of income/expense data
  - `get_net_worth` - total assets, liabilities, net worth (+ portfolio market value)
- **Endpoints**:
  - `GET /reports/category-breakdown`
  - `GET /reports/income-vs-expenses`
  - `GET /reports/monthly-trends`
  - `GET /reports/net-worth`
- **20 tests** covering all 4 report types

### 7. Connect Endpoint (`/api/v1/connect`)
- **Endpoints**:
  - `GET /connect/institutions?country=PL` - list available banks
  - `POST /connect/requisitions` - create a requisition link
  - `GET /connect/requisitions/{id}/poll` - poll status, auto-create accounts when LINKED
  - `GET /connect/connections` - list user's connections
  - `DELETE /connect/connections/{id}` - disconnect (revoke + deactivate accounts)
- **25 tests** covering all connect endpoints, dedup, edge cases

### 8. Category Seeding (`app/db/seed_categories.py`)
- Idempotent seeding of 12 system categories at app startup
- Triggered from `app/main.py` lifespan

### 9. Router Integration
- All endpoint modules registered in `app/api/v1/router.py`
- All services registered in `app/services/__init__.py`
- All models registered in `app/models/__init__.py`

## Test Summary
- **259 tests total**, all passing (21.6s, SQLite in-memory)
- 12 test files covering all features
- Pre-existing `test_auth.py` failures (passlib/bcrypt compat) - not caused by Sprint 2

## Test Infrastructure Fixes
- `conftest.py` - shared SQLite engine + `monkeypatch.setattr` patching of `SessionLocal` in modules that import it directly (fixes MSSQL connection timeout when tasks create their own session)
- `pytest.ini` - `asyncio_default_fixture_loop_scope = function` to suppress deprecation warning
- Added `PLAID` to `BankProvider` enum (was `LookupError` in tests setting provider to "plaid")

## Key Decisions
- Provider adapter pattern via ABC allows Plaid swap later without touching pipeline code
- Ingestion uses check-then-insert dedup via `dedupe_hash` unique constraint
- Rule-based classification runs BEFORE ML pipeline - ML only for unmatched descriptions
- Connect `poll_requisition` checks `already_linked` before calling provider; `_sync_provider_accounts` idempotent via `external_account_id`
- Portfolio `compute_summary` includes both Account balances + Holding market values for net worth
- Budget service uses `abs(spent)` so remaining/progress calculations are positive
