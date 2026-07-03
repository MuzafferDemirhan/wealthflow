# Sprint 0 - Project Scaffolding

## Goal
Set up the full-stack project foundation: Docker environment, database schema, CI/CD, and core application structure.

## Deliverables

### Docker Infrastructure
- `docker-compose.yml` - MS SQL Server 2022, Redis 7, backend (FastAPI), frontend (Next.js)
- Dockerfiles for backend and frontend
- Volume mounts for persistent DB data
- Health checks and dependency ordering

### Backend Scaffolding (`backend/`)
- **FastAPI** application with lifespan management
- **SQLAlchemy 2.0** ORM setup with Base, UUID PK mixin, timestamp mixin
- **Alembic** migrations (autogenerate-enabled)
- **Pydantic v2** settings via `pydantic-settings` (`.env` file support)
- **Redis** connection via `redis-py`
- **Celery** task queue with Redis broker (beat schedule placeholder)
- CORS middleware config
- Health check endpoint (`GET /health`)

### Initial Data Models
- `User` (id, email, hashed_password, full_name, role, is_active)
- `Category` (id, name, slug, icon, is_system, user_id)
- `BankConnection` (id, user_id, provider, institution, status, external_reference)
- `Account` (id, user_id, bank_connection_id, external_account_id, display_name, type, currency, balance)
- `Transaction` (id, account_id, category_id, external_id, amount, currency, booking_date, status, description, counterparty)
- `Budget` (id, user_id, category_id, period_month, amount_limit, currency)
- `RefreshToken` (id, user_id, token, expires_at)

### CI/CD
- GitHub Actions workflow (`ci.yml`) - lint (ruff), type-check (pyright), test (pytest), Docker build

### Project Documentation
- Software Requirements Specification (`docs/SRS/`)
- System Architecture Diagram + docs
- ER Diagram + docs

## Key Decisions
- **MS SQL Server 2022** as primary database (mssql+pyodbc)
- **SQLite in-memory** for tests (conftest.py pattern with `override_get_db`)
- **Sync SQLAlchemy engine** (not async) - pyodbc/aioodbc async stack is immature
- **ruff** for linting (select E, F, I; ignore E501, F401)
- **JWT token pair** (access + refresh) for auth
- **python-jose** for JWT handling
