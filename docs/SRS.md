# Software Requirements Specification
## WealthFlow — Personal Finance & Investment Platform
**Version:** 1.0.0-DRAFT  
**Date:** 2026-06-29  
**Status:** Draft  

---

## Table of Contents
1. [Introduction](#1-introduction)
2. [Overall Description](#2-overall-description)
3. [Functional Requirements](#3-functional-requirements)
4. [Non-Functional Requirements](#4-non-functional-requirements)
5. [System Architecture](#5-system-architecture)
6. [Database Schema](#6-database-schema)
7. [API Specification](#7-api-specification)
8. [Tech Stack](#8-tech-stack)
9. [Scrum Plan](#9-scrum-plan)
10. [Risks & Mitigations](#10-risks--mitigations)

---

## 1. Introduction

### 1.1 Purpose
This document defines the software requirements for **WealthFlow**, a full-stack personal finance and investment tracking platform. It serves as the single source of truth for all development decisions and is updated iteratively as the project evolves.

### 1.2 Scope
WealthFlow allows users to:
- Connect bank accounts via Open Banking APIs (Plaid/Nordigen)
- Automatically categorize transactions using a machine learning classifier
- Track investment portfolios (stocks, crypto, funds)
- Set budgets and receive real-time alerts
- Get AI-powered financial advice via a chatbot
- Export reports as PDF or CSV

### 1.3 Target Audience
- **Primary users:** Professionals aged 25–40 managing multiple income streams and investments
- **Market:** EU/Poland (PSD2-compliant Open Banking)

### 1.4 Definitions
| Term | Definition |
|------|------------|
| Open Banking | Standard allowing third-party access to bank data via APIs under PSD2 |
| PSD2 | EU Payment Services Directive 2 — mandates Open Banking |
| JWT | JSON Web Token — stateless authentication mechanism |
| ML | Machine learning model for transaction classification |

---

## 2. Overall Description

### 2.1 Product Perspective
WealthFlow is a standalone web application with a REST API backend. It integrates with:
- **Plaid / Nordigen** for bank account data
- **Alpha Vantage / Yahoo Finance** for market data
- **Anthropic Claude API** for the AI financial advisor chatbot

### 2.2 User Classes
| User Class | Description |
|------------|-------------|
| Authenticated User | Full access to all features |
| Guest | Landing page only, no data access |
| Admin | User management, system monitoring |

### 2.3 Operating Environment
- **Frontend:** Modern browsers (Chrome 120+, Firefox 120+, Safari 17+)
- **Backend:** Linux (Ubuntu 22.04 LTS) via Docker
- **Database:** PostgreSQL 16
- **Deployment:** Railway (MVP), scalable to AWS/GCP

---

## 3. Functional Requirements

### 3.1 Authentication & Authorization
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01 | User registration with email + password | High |
| FR-02 | Login with JWT access + refresh tokens | High |
| FR-03 | OAuth2 social login (Google) | Medium |
| FR-04 | Password reset via email | Medium |
| FR-05 | Role-based access control (user/admin) | High |

### 3.2 Bank Account Integration
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-06 | Connect bank accounts via Plaid Link / Nordigen | High |
| FR-07 | Fetch and store transaction history (90 days) | High |
| FR-08 | Real-time balance updates via webhooks | Medium |
| FR-09 | Support multiple accounts per user | High |
| FR-10 | Disconnect account and delete associated data | High |

### 3.3 Transaction Management
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-11 | Auto-categorize transactions using ML model | High |
| FR-12 | Manual category override by user | High |
| FR-13 | Search and filter transactions | Medium |
| FR-14 | Add manual transactions (cash) | Low |
| FR-15 | Recurring transaction detection | Medium |

### 3.4 Dashboard & Analytics
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-16 | Monthly income vs expense chart | High |
| FR-17 | Spending breakdown by category (pie/donut chart) | High |
| FR-18 | Net worth over time (line chart) | High |
| FR-19 | Cash flow heatmap (daily spending) | Medium |
| FR-20 | Savings rate calculation | Medium |

### 3.5 Budget Management
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-21 | Create monthly budgets per category | High |
| FR-22 | Progress bar tracking against budget | High |
| FR-23 | Push notification when 80% of budget used | Medium |
| FR-24 | Budget history and comparison | Low |

### 3.6 Investment Portfolio
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-25 | Add holdings (ticker, shares, purchase price) | High |
| FR-26 | Real-time price fetch from market API | High |
| FR-27 | Portfolio performance (P&L, %) | High |
| FR-28 | Asset allocation pie chart | Medium |
| FR-29 | Historical portfolio value chart | Medium |

### 3.7 AI Financial Advisor
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-30 | Chatbot powered by Claude API | Medium |
| FR-31 | Context-aware (knows user's transactions/budgets) | Medium |
| FR-32 | Suggest savings opportunities | Low |
| FR-33 | Persistent chat history | Low |

### 3.8 Reports & Export
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-34 | Monthly PDF report generation | Medium |
| FR-35 | CSV export of transactions | Medium |
| FR-36 | Email delivery of reports | Low |

---

## 4. Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-01 | API response time (p95) | < 200ms |
| NFR-02 | Uptime SLA | 99.9% |
| NFR-03 | Data encryption at rest | AES-256 |
| NFR-04 | Data encryption in transit | TLS 1.3 |
| NFR-05 | GDPR compliance | Full — right to deletion, data export |
| NFR-06 | OWASP Top 10 | All mitigated |
| NFR-07 | Lighthouse performance score | > 90 |
| NFR-08 | Mobile responsive | All breakpoints |
| NFR-09 | Test coverage | > 80% (unit + integration) |
| NFR-10 | API rate limiting | 100 req/min per user |

---

## 5. System Architecture

```
┌─────────────────────────────────────────────────────┐
│                     CLIENT LAYER                     │
│         Next.js 15 + TypeScript (Vercel/Railway)     │
└──────────────────────┬──────────────────────────────┘
                       │ HTTPS / WebSocket
┌──────────────────────▼──────────────────────────────┐
│                    API GATEWAY                       │
│           FastAPI + Uvicorn (Python 3.12)            │
├────────────────────────────────────────────────────-─┤
│  Auth Module  │  Finance Module  │  ML Module        │
│  JWT + OAuth2 │  Transactions    │  Classifier       │
│               │  Budgets         │  (scikit-learn)   │
│               │  Portfolio       │                   │
└───────┬───────┴────────┬─────────┴──────────────────┘
        │                │
┌───────▼──────┐  ┌──────▼───────┐  ┌────────────────┐
│  PostgreSQL  │  │    Redis     │  │  Celery Worker │
│  (Primary)   │  │  (Cache +    │  │  (Async tasks: │
│              │  │   Sessions)  │  │  reports, notif│
└──────────────┘  └──────────────┘  └────────────────┘
        │
┌───────▼────────────────────────────────────────────┐
│                EXTERNAL SERVICES                    │
│  Plaid/Nordigen │ Alpha Vantage │ Claude API        │
└────────────────────────────────────────────────────┘
```

---

## 6. Database Schema

### Core Tables

```sql
-- Users
CREATE TABLE users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       VARCHAR(255) UNIQUE NOT NULL,
    hashed_pw   VARCHAR(255),
    full_name   VARCHAR(255),
    is_active   BOOLEAN DEFAULT TRUE,
    is_admin    BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Bank Accounts
CREATE TABLE accounts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    provider        VARCHAR(50) NOT NULL, -- 'plaid' | 'nordigen'
    external_id     VARCHAR(255) NOT NULL,
    institution     VARCHAR(255),
    account_type    VARCHAR(50), -- checking | savings | credit
    balance         NUMERIC(15,2),
    currency        VARCHAR(3) DEFAULT 'PLN',
    last_synced_at  TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Transactions
CREATE TABLE transactions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id      UUID REFERENCES accounts(id) ON DELETE CASCADE,
    external_id     VARCHAR(255) UNIQUE,
    amount          NUMERIC(15,2) NOT NULL,
    currency        VARCHAR(3) DEFAULT 'PLN',
    description     TEXT,
    category_id     UUID REFERENCES categories(id),
    is_manual       BOOLEAN DEFAULT FALSE,
    date            DATE NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Categories
CREATE TABLE categories (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(100) NOT NULL,
    icon        VARCHAR(50),
    color       VARCHAR(7),
    is_default  BOOLEAN DEFAULT FALSE
);

-- Budgets
CREATE TABLE budgets (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    category_id UUID REFERENCES categories(id),
    amount      NUMERIC(15,2) NOT NULL,
    period      VARCHAR(20) DEFAULT 'monthly',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Portfolio Holdings
CREATE TABLE holdings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    ticker          VARCHAR(20) NOT NULL,
    shares          NUMERIC(15,6) NOT NULL,
    avg_cost        NUMERIC(15,2) NOT NULL,
    asset_type      VARCHAR(20), -- stock | crypto | etf | fund
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 7. API Specification

### Base URL: `/api/v1`

#### Authentication
```
POST   /auth/register          Register new user
POST   /auth/login             Login, returns JWT pair
POST   /auth/refresh           Refresh access token
POST   /auth/logout            Invalidate refresh token
POST   /auth/password-reset    Send reset email
```

#### Accounts
```
GET    /accounts               List user's connected accounts
POST   /accounts/connect       Initiate Open Banking connection
DELETE /accounts/{id}          Disconnect account
GET    /accounts/{id}/sync     Force sync transactions
```

#### Transactions
```
GET    /transactions           List (filter: date, category, account)
GET    /transactions/{id}      Get single transaction
PATCH  /transactions/{id}      Update category
POST   /transactions           Create manual transaction
```

#### Budgets
```
GET    /budgets                List budgets with progress
POST   /budgets                Create budget
PUT    /budgets/{id}           Update budget
DELETE /budgets/{id}           Delete budget
```

#### Portfolio
```
GET    /portfolio              Holdings with current prices + P&L
POST   /portfolio/holdings     Add holding
DELETE /portfolio/holdings/{id} Remove holding
```

#### Reports
```
GET    /reports/monthly        Monthly summary (JSON)
GET    /reports/pdf            Download PDF report
GET    /reports/csv            Download transactions CSV
```

---

## 8. Tech Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| Frontend | Next.js 15 + TypeScript | SSR, type safety, strong EU job market demand |
| Styling | Tailwind CSS | Rapid UI development |
| Charts | Recharts | React-native charting |
| Backend | FastAPI (Python 3.12) | Async, auto-docs, ML-friendly |
| ORM | SQLAlchemy 2.0 + Alembic | Type-safe queries, migrations |
| Database | PostgreSQL 16 | ACID, JSON support, mature |
| Cache | Redis 7 | Session store, rate limiting |
| Task Queue | Celery + Redis broker | Async jobs (reports, notifications) |
| ML | scikit-learn | Transaction classifier |
| Auth | JWT + python-jose | Stateless, scalable |
| Containerization | Docker + Docker Compose | Reproducible environments |
| CI/CD | GitHub Actions | Automated test + deploy |
| Deployment | Railway | Simple PaaS, free tier |
| Testing | pytest + React Testing Library | >80% coverage target |

---

## 9. Scrum Plan

### Sprint 0 — Foundation (Week 1)
- [x] SRS document
- [ ] System architecture diagram
- [ ] Database ERD
- [ ] Project scaffolding (repo structure, Docker Compose)

### Sprint 1 — Backend Core (Weeks 2–3)
- [ ] FastAPI project setup with folder structure
- [ ] PostgreSQL + Alembic migrations
- [ ] User model + JWT auth endpoints
- [ ] Docker Compose (FastAPI + PostgreSQL + Redis)
- [ ] GitHub Actions CI (lint + test)

### Sprint 2 — Data Layer (Weeks 4–5)
- [ ] Plaid/Nordigen integration (sandbox)
- [ ] Transaction ingestion pipeline
- [ ] ML classifier for categories (scikit-learn)
- [ ] Celery worker setup
- [ ] REST endpoints: accounts, transactions, budgets

### Sprint 3 — Frontend (Weeks 6–7)
- [ ] Next.js project setup + Tailwind
- [ ] Auth pages (login, register)
- [ ] Dashboard with Recharts
- [ ] Transactions list + filter
- [ ] Portfolio view

### Sprint 4 — AI & Polish (Week 8)
- [ ] Claude API chatbot integration
- [ ] WebSocket notifications
- [ ] PDF report generation (ReportLab)
- [ ] Railway deployment
- [ ] End-to-end tests

### Launch (Week 9)
- [ ] English README with screenshots
- [ ] Demo GIF
- [ ] GitHub profile pinning
- [ ] LinkedIn post

---

## 10. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Open Banking API rate limits | Medium | High | Cache responses in Redis, use webhooks |
| ML classifier low accuracy | Medium | Medium | Start with rule-based fallback |
| GDPR non-compliance | Low | High | Encrypt PII, implement data deletion |
| Railway downtime | Low | Medium | Health checks, auto-restart |
| Scope creep | High | Medium | Strict sprint backlog, MoSCoW prioritization |

---

*This document is a living artifact. It will be updated at the end of each sprint.*
