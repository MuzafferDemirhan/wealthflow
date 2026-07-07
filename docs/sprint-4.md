# Sprint 4 - AI Chatbot, Reports Export, and Deployment

## Goal
Integrate an AI financial advisor chatbot powered by Groq (free-tier LLM API), add PDF/CSV report export with WebSocket notifications, and deploy to production on Railway.

## AI Chatbot Flow

```mermaid
sequenceDiagram
    participant User as User
    participant Chat as Chat Page
    participant WS as WebSocket
    participant API as Chat API
    participant Service as Chat Service
    participant LLM as Groq API

    User->>Chat: Type message
    Chat->>Chat: Append user message to history
    Chat->>API: POST /chat/messages (message + context)
    API->>Service: process_message(user_id, message)

    Service->>Service: Build system prompt with<br/>user's financial context
    Service->>Service: Fetch recent transactions<br/>budgets, net worth
    Service->>LLM: OpenAI-compatible<br/>chat completions API
    LLM-->>Service: Assistant response

    Service->>Service: Save chat message to DB
    Service-->>API: { response, conversation_id }
    API-->>Chat: Assistant message
    Chat->>Chat: Append assistant message

    alt Budget alert triggered
        Service->>WS: Push notification to user
        WS-->>Chat: { type: "budget_alert", ... }
        Chat->>Chat: Show notification toast
    end
```

## WebSocket Notification Flow

```mermaid
sequenceDiagram
    participant User as User
    participant FE as Frontend
    participant WS as WebSocket Manager
    participant BE as Backend API
    participant Celery as Celery Worker

    User->>FE: Login
    FE->>WS: WebSocket connect (with token)
    WS->>WS: Authenticate + register connection

    Celery->>BE: sync_account_transactions completes
    BE->>BE: Check budget threshold (80%/100%)
    alt Budget threshold crossed
        BE->>WS: Send notification to user channel
        WS-->>FE: { type: "budget_alert", category, spent, limit }
        FE->>FE: Show toast notification
    end

    alt Transaction sync complete
        BE->>WS: Send notification
        WS-->>FE: { type: "sync_complete", account, count }
        FE->>FE: Show toast + refresh data
    end

    User->>FE: Navigate away / close tab
    FE->>WS: Disconnect
```

## Report Export Flow

```mermaid
sequenceDiagram
    participant User as User
    participant FE as Frontend
    participant BE as Backend API
    participant Service as Report Service
    participant Celery as Celery Worker

    User->>FE: Click "Export PDF" or "Export CSV"
    FE->>BE: POST /reports/export (type: pdf/csv, report_type, params)

    alt Small report (inline)
        BE->>Service: generate_report(report_type, format, params)
        Service->>Service: Fetch data from DB
        Service->>Service: Build PDF (ReportLab) or CSV
        Service-->>BE: BytesIO
        BE-->>FE: Streaming response (application/pdf or text/csv)
        FE->>User: File download
    else Large report (async)
        BE->>Celery: generate_report_async.delay(...)
        BE-->>FE: { task_id, status: "processing" }
        FE->>FE: Show progress indicator
        Celery-->>WS: { type: "report_ready", task_id, url }
        WS-->>FE: Notification received
        FE->>BE: GET /reports/export/{task_id}/download
        BE-->>FE: File download
    end
```

## Railway Deployment Architecture

```mermaid
graph TB
    subgraph Railway
        subgraph Network
            CF[Cloudflare<br/>DNS + SSL]
        end

        subgraph Services ["Railway Services"]
            BE[Backend<br/>FastAPI<br/>Port 8000]
            CW[Celery Worker]
            CB[Celery Beat]
            FE[Frontend<br/>Next.js<br/>Port 3000]
            MSSQL[MS SQL Server 2022]
            RD[Redis<br/>Railway Addon | Local in MVP]
        end

        subgraph External
            PLAID[Plaid API]
            GROQ[Groq API<br/>Free LLM tier]
            AV[Alpha Vantage]
        end

        CF --> FE
        CF --> BE
        BE --> MSSQL
        BE --> RD
        BE --> GROQ
        BE --> PLAID
        BE --> AV
        CW --> RD
        CB --> RD
        FE --> BE
    end
```

## Deliverables

### 1. AI Financial Advisor Chatbot

#### Backend (`backend/app/`)

| Component | File | Description |
|-----------|------|-------------|
| Chat model | `models/chat_message.py` | `ChatMessage` (id, user_id, role, content, conversation_id, created_at) |
| Chat schema | `schemas/chat.py` | SendMessage, ChatResponse, ChatHistory |
| Chat service | `services/chat_service.py` | System prompt builder, Groq API client (OpenAI-compatible), context injection |
| Chat endpoint | `api/v1/endpoints/chat.py` | `POST /chat/messages`, `GET /chat/history`, `DELETE /chat/history` |
| Model registration | `models/__init__.py` | Import `ChatMessage` |

**Chat service details:**

| Method | Description |
|--------|-------------|
| `process_message(user_id, message, conversation_id)` | Calls Ollama, saves to DB, returns response |
| `get_conversation_history(user_id, conversation_id)` | Returns recent N messages for context |
| `delete_conversation(user_id, conversation_id)` | Deletes chat history |
| `_build_system_prompt(user_id)` | Injects user financial context (total balance, recent transactions, budget status, net worth) |
| `_call_llm(messages)` | Core HTTP call to Groq's OpenAI-compatible API |

**System prompt context injection:**
- Total account balance across all accounts
- Recent 10 transactions with categories
- Active budgets with spending vs limit
- Net worth summary
- Cached and refreshed every 5 minutes

**Configuration (`core/config.py`):**
- `LLM_BASE_URL: str = "https://api.groq.com/openai/v1"` — OpenAI-compatible endpoint (Groq, OpenRouter, etc.)
- `LLM_API_KEY: str = ""` — Groq API key from https://console.groq.com/keys
- `LLM_MODEL: str = "llama-3.3-70b-versatile"` — Model to use (free tier: `llama-3.3-70b-versatile`, `llama-3.1-8b-instant`)
- Remove `CLAUDE_API_KEY` field (no longer needed)

#### Frontend (`frontend/src/`)

| Component | Path | Description |
|-----------|------|-------------|
| Chat page | `app/(dashboard)/chat/page.tsx` | Full-page chat interface |
| Chat messages | `components/chat/ChatMessage.tsx` | Single message bubble (user/assistant) |
| Chat input | `components/chat/ChatInput.tsx` | Text input + send button |
| Chat hook | `hooks/useChat.ts` | Message state, API calls, auto-scroll |

**Chat page features:**
| Feature | Description |
|---------|-------------|
| Message list | Scrollable container with auto-scroll to bottom |
| User/assistant bubbles | Distinct styling for user vs assistant messages |
| Typing indicator | Animated dots while waiting for LLM response |
| Conversation persistence | Messages saved and loaded from backend |
| Clear history | Button to delete conversation |
| Suggested prompts | Quick-action buttons ("How am I spending?", "Budget check", "Savings tips") |
| Error handling | Retry on failure, graceful degradation |

### 2. WebSocket Notifications

#### Backend

| Component | File | Description |
|-----------|------|-------------|
| WebSocket manager | `core/websocket_manager.py` | `WebSocketManager` singleton: connect, disconnect, send_to_user, broadcast |
| Auth dependency | `core/websocket_manager.py` | Token-based WS authentication |
| Notification model | `models/notification.py` | `Notification` (id, user_id, type, title, body, payload, is_read, created_at) |
| Notification schema | `schemas/notification.py` | NotificationOut, MarkRead |
| Notification endpoint | `api/v1/endpoints/notifications.py` | `GET /notifications`, `PATCH /notifications/{id}/read`, `GET /notifications/unread-count` |
| App startup | `main.py` lifespan | Initialize `WebSocketManager` |
| Dependency injection | `core/dependencies.py` | `get_ws_manager()` provider |

**WebSocket protocol:**
```
Client → Server:  ws://host/api/v1/ws?token=<access_token>
Server → Client:  {"type": "connected", "user_id": "..."}
Server → Client:  {"type": "notification", "data": NotificationOut}
Server → Client:  {"type": "budget_alert", "data": {...}}
Server → Client:  {"type": "sync_complete", "data": {...}}
Client → Server:  {"type": "ping"}
Server → Client:  {"type": "pong"}
```

**Notification types:**

| Type | Trigger | Payload |
|------|---------|---------|
| `budget_alert` | Budget usage hits 80% or 100% | `{ category, spent, limit, percentage }` |
| `sync_complete` | Transaction sync finishes | `{ account_name, transaction_count }` |
| `report_ready` | Async report generation done | `{ task_id, report_type, format }` |

**Celery integration:**
- `app/tasks/notifications.py` — `send_budget_alert(notification_id)` and `notify_sync_complete(connection_id, count)`
- Uses `WebSocketManager.send_to_user()` from within Celery via Redis pub/sub bridge

#### Frontend

| Component | Path | Description |
|-----------|------|-------------|
| WS hook | `hooks/useWebSocket.ts` | Connect/disconnect/reconnect, message routing, heartbeat |
| Toast integration | `components/ui/Toast.tsx` | Extend existing Toast to handle notification display |
| Notification badge | `components/layout/Header.tsx` | Unread count badge on bell icon |

**Frontend WebSocket hook (`useWebSocket`):**

| Feature | Detail |
|---------|--------|
| Connection | Connects on auth, disconnects on logout |
| Reconnect | Exponential backoff (1s, 2s, 4s, 8s, max 30s) |
| Heartbeat | Ping every 30 seconds |
| Message routing | Dispatches to callbacks by type |
| State | `useRef` for stable socket reference, `useState` for connection status |

**Notification display:**
- Push notifications appear via the existing `Toast` component
- Bell icon in `Header` shows unread count badge
- Clicking bell opens notification drawer/panel
- Each notification can be marked as read via API call

### 3. PDF & CSV Report Export

#### Backend

| Component | File | Description |
|-----------|------|-------------|
| Report generation | `services/export_service.py` | `generate_pdf_report()`, `generate_csv_transactions()`, `generate_report()` dispatcher |
| Export endpoint | `api/v1/endpoints/export.py` | `POST /reports/export` (trigger sync or async), `GET /reports/export/{task_id}/download`, `GET /reports/export/{task_id}/status` |
| Export schema | `schemas/export.py` | `ExportRequest`, `ExportTask`, `ExportStatus` |
| PDF generation (sync) | `services/export_service.py` | ReportLab `SimpleDocTemplate`, tables for transaction data, charts via matplotlib, header/footer with date range |
| CSV generation | `services/export_service.py` | Standard library `csv` module, streaming response |
| Router registration | `api/v1/router.py` | Include export router |

**Export API:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/reports/export` | Trigger export. Body: `{ report_type, format, params }`. Returns inline bytes if small, `{ task_id }` if large. |
| GET | `/reports/export/{task_id}/status` | Poll async task status (pending/processing/done/error) |
| GET | `/reports/export/{task_id}/download` | Download completed file |

**Report types available for export:**

| Type | Description | PDF | CSV |
|------|-------------|-----|-----|
| `category-breakdown` | Spending by category | Table + pie chart | ✅ |
| `income-vs-expenses` | Income vs expenses | Table + bar chart | ✅ |
| `monthly-trends` | Monthly trends | Table + line chart | ✅ |
| `net-worth` | Net worth snapshot | Table + card | ✅ |
| `transactions` | Full transaction list | Table | ✅ (filtered) |

**PDF report layout:**
```
+---------------------------------------+
|  WealthFlow Monthly Report            |
|  Date Range: 2026-07-01 – 2026-07-31  |
+---------------------------------------+
|  Summary Section                      |
|  • Total Income: 12,500.00 PLN        |
|  • Total Expenses: 8,300.00 PLN       |
|  • Net: 4,200.00 PLN                  |
|  • Net Worth: 125,000.00 PLN          |
+---------------------------------------+
|  Category Breakdown Table             |
|  Category        | Amount   | %       |
|  ----------------|----------|---------|
|  Housing         | 3,000.00 | 36.1%   |
|  Groceries       | 1,500.00 | 18.1%   |
|  ...             | ...      | ...     |
+---------------------------------------+
|  (Charts embedded as images)          |
+---------------------------------------+
|  Generated: 2026-07-31                |
+---------------------------------------+
```

**Decision: ReportLab vs weasyprint:**

| Choice | Rationale |
|--------|-----------|
| ReportLab | No external HTML/CSS rendering dependencies, pure Python, full control over layout, no system font deps |

#### Frontend

| Component | Path | Description |
|-----------|------|-------------|
| Export button | `components/reports/ExportButton.tsx` | Dropdown with PDF/CSV options |
| Export dialog | `components/reports/ExportDialog.tsx` | Date range picker + format selector |
| Toast feedback | Integration | "Report generated" / "Download started" notifications |

**Frontend integration:**
- Each report page gets an "Export" button in its header/action area
- Click opens `ExportDialog` where user selects format and date range
- On submit, calls `POST /reports/export` with params
- For sync responses: triggers browser download via blob URL
- For async responses: shows progress toast, waits for WebSocket `report_ready` notification, then downloads

### 4. Railway Deployment

| Task | File | Description |
|------|------|-------------|
| Root config | `railway.json` | Builder + deploy hints for Railway |
| Deploy workflow | `.github/workflows/deploy.yml` | GitHub Action to deploy on push to `main` |
| Backend Dockerfile | `backend/Dockerfile` | Multi-stage Python 3.12-slim + ODBC driver |
| Frontend Dockerfile | `frontend/Dockerfile` | Multi-stage Next.js standalone build |
| Database migration | `backend/entrypoint.sh` | Auto-run `alembic upgrade head` on backend start |
| Health check | `GET /health` | Used by Railway for readiness probe |

**Project structure on Railway (4 services):**

| Service | Source | Port | Command |
|---------|--------|------|---------|
| `backend` | `backend/Dockerfile` | 8000 | `uvicorn app.main:app --host 0.0.0.0 --port 8000` |
| `frontend` | `frontend/Dockerfile` (target: runner) | 3000 | `node server.js` |
| `celery-worker` | `backend/Dockerfile` | — | `celery -A app.core.celery_app worker --loglevel=info` |
| `celery-beat` | `backend/Dockerfile` | — | `celery -A app.core.celery_app beat --loglevel=info` |

**railway.json:**
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE"
  },
  "deploy": {
    "numReplicas": 1,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 3
  }
}
```

**Required Railway environment variables (set per-service):**

| Variable | Source | Notes |
|----------|--------|-------|
| `DATABASE_URL` | Railway MS SQL / external host | `mssql+pyodbc://user:pass@host:1433/db?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes` |
| `REDIS_URL` | Railway Redis plugin or Upstash | `redis://...` |
| `SECRET_KEY` | `openssl rand -hex 32` | Production secret |
| `PLAID_CLIENT_ID` | Plaid Dashboard | Sandbox or production |
| `PLAID_SECRET` | Plaid Dashboard | Sandbox or production |
| `LLM_BASE_URL` | Groq API | `https://api.groq.com/openai/v1` |
| `LLM_API_KEY` | Groq Console | From https://console.groq.com/keys |
| `LLM_MODEL` | Groq model | `llama-3.3-70b-versatile` |
| `ALPHA_VANTAGE_KEY` | Alpha Vantage | Market data API |
| `TOKEN_ENCRYPTION_KEY` | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` | Token encryption |
| `ALLOWED_ORIGINS` | Railway frontend URL | Comma-separated, e.g. `https://frontend.railway.app` |
| `NEXT_PUBLIC_API_URL` | Railway backend URL | e.g. `https://backend.railway.app/api/v1` (frontend service only) |

**Deploy workflow (`.github/workflows/deploy.yml`):**

```yaml
# Triggered on push to main or manual workflow_dispatch
# Steps:
#   1. actions/checkout@v4
#   2. npm install -g @railway/cli
#   3. railway up --service backend
#   4. railway up --service celery-worker
#   5. railway up --service celery-beat
#   6. railway up --service frontend
#   7. railway run --service backend "alembic upgrade head"
#
# Requires: RAILWAY_TOKEN secret in GitHub repo settings.
# Generate token at: https://railway.app/account/tokens
```

**Setup steps (one-time):**
1. Push repo to GitHub
2. Create Railway project from GitHub repo
3. Add 4 services (backend, frontend, celery-worker, celery-beat) linked to their Dockerfiles
4. Set environment variables per service in Railway dashboard
5. Add `RAILWAY_TOKEN` to GitHub repo secrets
6. Push to `main` — deploy workflow runs automatically

### 5. Testing Strategy

#### Backend Unit Tests

| Module | Tests | Coverage |
|--------|-------|----------|
| Chat service | 15 | Message processing, system prompt building, Ollama API call (mocked), conversation history, error handling |
| Chat endpoint | 10 | Send message, get history, delete history, auth scoping |
| WebSocket manager | 10 | Connect/disconnect, authentication, send_to_user, broadcast, concurrent connections |
| Notification model | 5 | CRUD, mark as read, unread count |
| Notification endpoint | 8 | List, mark read, unread count, auth scoping |
| Export service (PDF) | 12 | PDF generation for each report type, formatting, file size sanity, empty data |
| Export service (CSV) | 8 | CSV generation for transactions + reports, encoding, field mapping |
| Export endpoint | 10 | Trigger export, poll status, download, error handling, auth scoping |

#### Frontend Unit Tests (Vitest + RTL)

| Component | Tests | Coverage |
|-----------|-------|----------|
| ChatMessage | 4 | User bubble, assistant bubble, markdown rendering, timestamp |
| ChatInput | 3 | Send on enter, send on click, disabled while loading |
| Chat page | 4 | Message list render, loading state, empty state, error state |
| useChat hook | 4 | Send message, load history, clear history, error handling |
| useWebSocket hook | 5 | Connect, disconnect, reconnection, message routing, heartbeat |
| ExportButton | 3 | Dropdown render, PDF click, CSV click |
| ExportDialog | 4 | Open, close, date range validation, submit |

#### E2E Tests (Playwright) — 10 new tests

| Category | Count | Description |
|----------|-------|-------------|
| Chat | 4 | Send message and see response, suggested prompts, clear history, error handling |
| Notifications | 3 | Notification toast appears, bell badge updates, notification drawer |
| Export | 3 | PDF export triggers download, CSV export triggers download, export from report page |

#### CI Integration

| Job | Command | Description |
|-----|---------|-------------|
| `backend-lint` | `ruff check .` | Python linting |
| `backend-test` | `pytest` | All backend tests (existing + new) |
| `frontend-lint` | `npm run lint` | ESLint |
| `frontend-test` | `npm test` | Vitest unit tests |
| `frontend-build` | `npm run build` | Type-check + production build |
| `deploy` | Railway CLI | Deploy to production (main branch only) |

### 6. Dependencies Added

#### Backend (`requirements.txt`)

| Package | Version | Purpose |
|---------|---------|---------|
| `websockets` | >=13.0 | WebSocket server support |
| `reportlab` | >=4.2 | PDF generation |
| `httpx` | already present | HTTP client for Ollama API (OpenAI-compatible) |

> **No `anthropic` SDK needed** — Groq exposes an OpenAI-compatible REST API, so the chat service calls it via `httpx` directly. This avoids vendor lock-in and makes it trivially swappable to any OpenAI-compatible provider (OpenRouter, LocalAI, etc.).

#### Frontend (`package.json`)

| Package | Version | Purpose |
|---------|---------|---------|
| No new frontend deps | — | Use native `WebSocket` API for WS, native `fetch` for API calls |

### 7. Groq API Key (No Docker Service Needed)

Groq is a cloud API — no local model storage or Docker service required.

**Setup:**
1. Sign up at https://console.groq.com (free, no credit card)
2. Generate an API key
3. Set environment variable:
   ```
   LLM_BASE_URL=https://api.groq.com/openai/v1
   LLM_API_KEY=gsk_your_key
   LLM_MODEL=llama-3.3-70b-versatile
   ```

**Free tier limits:** 30 req/min, 14,400 req/day — more than sufficient for a personal finance assistant.

**Backend → Groq connection:**
- Chat service uses `httpx` to call `POST https://api.groq.com/openai/v1/chat/completions` with Bearer token auth
- OpenAI-compatible format — zero vendor lock-in, swappable to OpenRouter, LocalAI, etc. by changing three env vars

### 8. New Folder Structure

```
backend/app/
  api/v1/endpoints/
    chat.py              # NEW - Chat endpoints
    notifications.py     # NEW - Notification endpoints
    export.py            # NEW - Export endpoints
  core/
    websocket_manager.py # NEW - WebSocket connection manager
  models/
    chat_message.py      # NEW - ChatMessage model
    notification.py      # NEW - Notification model
  schemas/
    chat.py              # NEW - Chat schemas
    notification.py      # NEW - Notification schemas
    export.py            # NEW - Export schemas
  services/
    chat_service.py      # NEW - Chat service with Groq integration
    export_service.py    # NEW - PDF/CSV generation
  tasks/
    notifications.py     # NEW - Celery notification tasks

frontend/src/
  app/(dashboard)/
    chat/                # NEW - Chat page
  components/
    chat/                # NEW - Chat components
      ChatMessage.tsx
      ChatInput.tsx
    reports/
      ExportButton.tsx   # NEW
      ExportDialog.tsx   # NEW
  hooks/
    useChat.ts           # NEW
    useWebSocket.ts      # NEW
```

## Implementation Order

```mermaid
flowchart LR
    S1[1. Dependencies + Config]
    S2[2. WebSocket manager]
    S3[3. Notification model + endpoint]
    S4[4. Frontend useWebSocket hook]
    S5[5. Chat model + service]
    S6[6. Chat endpoint]
    S7[7. Frontend chat UI]
    S8[8. Export service PDF/CSV]
    S9[9. Export endpoint]
    S10[10. Frontend export UI]
    S11[11. Tests: backend]
    S12[12. Tests: frontend]
    S13[13. Railway deploy config]
    S14[14. CI/CD pipeline]
    S15[15. E2E tests]

    S1 --> S2 --> S3 --> S4
    S4 --> S5 --> S6 --> S7
    S1 --> S8 --> S9 --> S10
    S7 --> S11
    S10 --> S11
    S11 --> S12
    S12 --> S13
    S13 --> S14
    S14 --> S15
```

## Test Summary

| Category | Count | Status |
|----------|-------|--------|
| Chat service + endpoint | 25 | 🔄 Planned |
| WebSocket manager | 10 | 🔄 Planned |
| Notification model + endpoint | 13 | 🔄 Planned |
| Export service (PDF + CSV) | 20 | 🔄 Planned |
| Export endpoint | 10 | 🔄 Planned |
| Frontend chat components | 15 | 🔄 Planned |
| Frontend hooks (useChat, useWebSocket) | 9 | 🔄 Planned |
| Frontend export components | 7 | 🔄 Planned |
| E2E (chat, notifications, export) | 10 | 🔄 Planned |
| **New tests** | **119** | 🔄 |
| Existing backend tests | 259 | ✅ |
| Existing frontend unit tests | 40 | ✅ |
| Existing E2E tests | 15 | ✅ |
| **Grand total** | **433** | |

## Sprint 4 Completion Checklist

- [x] Add `websockets`, `reportlab` to `requirements.txt`
- [x] `WebSocketManager` class with connect/disconnect/send/authenticate
- [x] `Notification` model + `GET/PATCH /notifications`
- [x] Frontend `useWebSocket` hook with reconnect + heartbeat
- [x] Notification toast + bell badge in Header
- [x] `ChatMessage` model + `POST/GET/DELETE /chat/messages`
- [x] `ChatService` with Groq API integration + system prompt builder
- [x] Chat page (`/chat`) with message list, input, typing indicator, suggested prompts
- [x] `ExportService` with PDF (ReportLab) + CSV generation
- [x] `POST/GET /exports` endpoints (sync)
- [x] Frontend `ExportDialog` on all 4 report pages
- [x] `railway.json` + deploy workflow
- [ ] Railway deployment: all services healthy
- [x] 0 TypeScript errors, 0 lint warnings
- [x] CI pipeline passing: lint → test → build

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Chat persistence | DB-backed conversation history | Users can resume chats across sessions |
| WebSocket library | `websockets` (Uvicorn-native) | Zero additional infra, FastAPI has built-in WS support |
| Notification delivery | WS push + DB persistence | Real-time + history for missed notifications |
| PDF engine | ReportLab | Pure Python, no external HTML/CSS renderer, full layout control |
| Async reports | Celery for large datasets, sync for small | Responsive UX for large reports without blocking |
| Export trigger | POST endpoint with format param | Unified interface, extensible for future formats |
| Deployment target | Railway | Simple PaaS, free tier, Docker-native |
| Database | MS SQL Server 2022 | Consistent across dev/prod (no swap needed) |
| LLM provider | Groq (free-tier API) | $0 cost, zero local storage, 30 req/min free tier, OpenAI-compatible |
| LLM API protocol | OpenAI-compatible REST API | Drop-in replaceable with any OpenAI-compatible provider (OpenRouter, LocalAI) |
| Chat context refresh | 5-minute cache | Avoids rebuilding financial context on every message |
| Suggested prompts | Static list in frontend | Fast UX, no extra API call to generate suggestions |
