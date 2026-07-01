# WealthFlow 

> A full-stack personal finance and investment tracking platform built for the European market.

[![CI](https://github.com/MuzafferDemirhan/WealthFlow/actions/workflows/ci.yml/badge.svg)](https://github.com/MuzafferDemirhan/WealthFlow/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.12-blue)
![TypeScript](https://img.shields.io/badge/TypeScript-5.0-blue)
![MS SQL Server](https://img.shields.io/badge/MS%20SQL%20Server-2022-blue)

---

## What is this?

WealthFlow connects your bank accounts, tracks your spending with ML-powered categorization and monitors your investment portfolio in one place. Built with a PSD2-compliant Open Banking integration, it targets the European financial ecosystem (Poland and EU).

**Core features:**
-  Bank account connection via Open Banking (Plaid / Nordigen)
-  Automatic transaction categorization (scikit-learn ML model)
-  Investment portfolio tracker with real-time market data
-  Budget planning with smart alerts
-  AI financial advisor chatbot (Claude API)
-  PDF & CSV report export

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 15, TypeScript, Tailwind CSS, Recharts |
| Backend | FastAPI, Python 3.12, SQLAlchemy 2.0 |
| Database | MS SQL Server 2022 + Redis 7 |
| ML | scikit-learn (transaction classifier) |
| Task Queue | Celery + Redis |
| Auth | JWT (python-jose) + OAuth2 |
| DevOps | Docker, Docker Compose, GitHub Actions |
| Deployment | Railway |

---

## System Architecture

![WealthFlow System Architecture](./docs/architecture/WealthFlow_SystemArchitecture.png)

> **Note:** You can access the code-based version of the architecture in the [architecture.md](./docs/architecture/architecture.md) file.

---

## Entity-Relationship Diagram

![WealthFlow Entity Relationship Diagram](./docs/ER%20diagram/WealthFlow_ERDiagram.png)

> **Note:** You can access the code-based version of the architecture in the [erd.md](./docs/ER%20diagram/erd.md) file.

---

## How to Run

### Prerequisites
- Docker & Docker Compose
- Node.js 20+
- Python 3.12+

### 1. Clone the repository
```bash
git clone https://github.com/MuzafferDemirhan/Example.git
cd Example
```

### 2. Set up environment variables
```bash
copy backend\.env.example backend\.env
# Fill in: DATABASE_URL, REDIS_URL, PLAID_CLIENT_ID, PLAID_SECRET, CLAUDE_API_KEY
```

### 3. Start with Docker Compose
```bash
docker compose up --build
```

### 4. Run database migrations
```bash
docker compose exec backend alembic upgrade head

# Connect via SSMS: localhost,1433 | User: sa | Password: WealthFlow_2024!
```

### 5. Access the app
| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API docs | http://localhost:8000/docs |
| SSMS (Windows) | localhost,1433 — sa / WealthFlow_2024! |

### 6. Run tests
```bash
# Backend
docker compose exec backend pytest --cov=app --cov-report=term

# Frontend
cd frontend && npm test
```

---

## Project Structure

```
wealthflow/
├── backend/
│   ├── app/
│   │   ├── api/          # Route handlers
│   │   ├── core/         # Config, security, dependencies
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # Pydantic schemas
│   │   └── services/     # Business logic
│   ├── alembic/          # DB migrations
│   └── tests/
├── frontend/
│   └── src/
│       ├── app/          # Next.js App Router pages
│       ├── components/   # Reusable UI components
│       └── lib/          # API client, utilities
├── docs/
│   └── SRS.md            # Software Requirements Specification
├── docker-compose.yml
└── .github/workflows/    # CI/CD pipelines
```

---

## Roadmap

- [x] Sprint 0 - Project scaffolding (Docker, DB, CI/CD, SRS)
- [x] Sprint 1 - Backend core (auth, accounts, categories, budgets, transactions)
- [x] Sprint 2 - Open Banking integration + ML classifier + portfolio + reports + connect
- [ ] Sprint 3 - Frontend dashboard
- [ ] Sprint 4 - AI chatbot + reports + deployment

> Detailed sprint summaries: [`docs/sprint-0.md`](./docs/sprint-0.md), [`docs/sprint-1.md`](./docs/sprint-1.md), [`docs/sprint-2.md`](./docs/sprint-2.md)

---

## License

MIT © [Muzaffer Demirhan](https://github.com/MuzafferDemirhan)
