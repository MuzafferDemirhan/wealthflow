# Sprint 0 - Project Scaffolding

## Goal
Set up the full-stack project foundation: Docker environment, database schema, CI/CD, and core application structure.

## Docker Compose Startup Flow

```mermaid
sequenceDiagram
    participant DC as Docker Compose
    participant MSSQL as MS SQL Server 2022
    participant Redis as Redis 7
    participant BE as Backend (FastAPI)
    participant Celery as Celery Worker
    participant FE as Frontend (Next.js)

    DC->>MSSQL: Start (health check: 1433)
    DC->>Redis: Start (health check: 6379)
    MSSQL-->>DC: Healthy
    Redis-->>DC: Healthy
    DC->>BE: Start (depends_on: MSSQL, Redis)
    BE->>MSSQL: Run Alembic migrations
    BE->>Redis: Connect
    BE->>BE: Seed system categories
    BE-->>DC: Healthy (port 8000)
    DC->>Celery: Start (depends_on: BE)
    Celery->>Redis: Connect as broker
    Celery-->>DC: Ready
    DC->>FE: Start (depends_on: BE)
    FE-->>DC: Healthy (port 3000)
```

## Core Data Models

```mermaid
classDiagram
    class User {
        UUID id
        string email
        string hashed_password
        string full_name
        string role
        bool is_active
        datetime created_at
        datetime updated_at
    }
    class Category {
        UUID id
        string name
        string slug
        string icon
        bool is_system
        UUID user_id
    }
    class BankConnection {
        UUID id
        UUID user_id
        string provider
        string institution
        string status
        string external_reference
    }
    class Account {
        UUID id
        UUID user_id
        UUID bank_connection_id
        string external_account_id
        string display_name
        string type
        string currency
        decimal balance
    }
    class Transaction {
        UUID id
        UUID account_id
        UUID category_id
        string external_id
        decimal amount
        string currency
        date booking_date
        string status
        string description
        string counterparty
        string dedupe_hash
    }
    class Budget {
        UUID id
        UUID user_id
        UUID category_id
        int period_month
        decimal amount_limit
        string currency
    }
    class RefreshToken {
        UUID id
        UUID user_id
        string token
        datetime expires_at
    }

    User "1" --> "*" Account
    User "1" --> "*" Budget
    User "1" --> "*" BankConnection
    User "1" --> "*" RefreshToken
    BankConnection "1" --> "*" Account
    Account "1" --> "*" Transaction
    Category "1" --> "*" Transaction
    Category "1" --> "*" Budget
```

## Deliverables

### Docker Infrastructure

| Service | Image | Port | Health Check |
|---------|-------|------|-------------|
| **MS SQL Server 2022** | `mcr.microsoft.com/mssql/server:2022-latest` | 1433 | `pg_isready`-style SQL query |
| **Redis 7** | `redis:7-alpine` | 6379 | `redis-cli ping` |
| **Backend (FastAPI)** | Custom Dockerfile | 8000 | `GET /health` |
| **Frontend (Next.js)** | Custom Dockerfile | 3000 | HTTP 200 on `/` |

- Volume mounts for persistent DB data
- Dependency ordering via `depends_on` + health checks

### Backend Scaffolding (`backend/`)
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Web Framework | FastAPI | REST API with auto-docs |
| ORM | SQLAlchemy 2.0 | Type-safe queries |
| Migrations | Alembic | Autogenerate-enabled |
| Settings | Pydantic v2 | `.env` file support |
| Cache | Redis via `redis-py` | Session store, rate limiting |
| Task Queue | Celery + Redis | Async job processing |
| CORS | FastAPI middleware | Frontend origin allowlist |
| Health Check | `GET /health` | Docker readiness probe |

### Initial Data Models
- `User` (id, email, hashed_password, full_name, role, is_active)
- `Category` (id, name, slug, icon, is_system, user_id)
- `BankConnection` (id, user_id, provider, institution, status, external_reference)
- `Account` (id, user_id, bank_connection_id, external_account_id, display_name, type, currency, balance)
- `Transaction` (id, account_id, category_id, external_id, amount, currency, booking_date, status, description, counterparty)
- `Budget` (id, user_id, category_id, period_month, amount_limit, currency)
- `RefreshToken` (id, user_id, token, expires_at)

### CI/CD Pipeline

| Stage | Tool | Description |
|-------|------|-------------|
| Lint | `ruff` | Python linting (select E, F, I) |
| Type Check | `pyright` | Static type checking |
| Test | `pytest` | Run backend test suite |
| Build | Docker | Build backend + frontend images |

### Project Documentation
- [Software Requirements Specification](../SRS/SRS.md)
- [System Architecture Diagram](../architecture/architecture.md)
- [ER Diagram](../ER%20diagram/erd.md)

## Sprint 0 Completion Checklist

- [x] `docker-compose.yml` with all 4 services
- [x] Multi-stage Dockerfiles for backend and frontend
- [x] FastAPI app with lifespan + health check
- [x] SQLAlchemy 2.0 Base + UUID/timestamp mixins
- [x] Alembic migrations (autogenerate)
- [x] Pydantic v2 settings with `.env` support
- [x] Redis + Celery integration
- [x] CORS middleware
- [x] All 7 initial data models
- [x] GitHub Actions CI (lint + type-check + test + build)
- [x] SRS + Architecture + ERD documentation

## Key Decisions
| Decision | Choice | Rationale |
|----------|--------|-----------|
| Primary Database | MS SQL Server 2022 | ACID, JSON support, mature |
| Test Database | SQLite in-memory | Fast, isolated, no external deps |
| SQLAlchemy Engine | Sync (not async) | pyodbc/aioodbc async stack is immature |
| Linter | ruff | Fast, modern Python linter |
| Auth Tokens | JWT pair (access + refresh) | Stateless, scalable |
| JWT Library | python-jose | Mature, well-supported |
