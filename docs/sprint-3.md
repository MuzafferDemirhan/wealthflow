# Sprint 3 — Next.js Frontend & End-to-End Integration

## Goal
Build the full Next.js 15 frontend with TypeScript and Tailwind CSS, covering all backend API surfaces. Establish frontend testing patterns, Docker integration, and CI checks.

## Deliverables

### 1. Next.js Project Scaffolding (`frontend/`)
- **Init** via `npx create-next-app@latest frontend` with:
  - TypeScript (strict mode)
  - Tailwind CSS (v4 or v3 — match latest)
  - App Router (`src/app/` directory)
  - ESLint with `eslint-config-next`
- **Folder structure**:
  frontend/src/
    app/
      (auth)/             # login, register
      (dashboard)/        # authenticated layout with sidebar
        page.tsx          # dashboard home
        accounts/
        transactions/
        budgets/
        portfolio/
        reports/
        connect/
    components/
      ui/                 # Button, Input, Card, Table, Badge, Modal, Spinner, Select, Pagination, Toast
      layout/             # Sidebar, Header, AuthGuard
      charts/             # Recharts wrappers
    lib/
      api-client.ts       # fetch wrapper with auth interceptor
      auth-context.tsx    # AuthProvider + useAuth hook
      types.ts            # TypeScript types matching all backend schemas
    hooks/
- **Dockerfile** (multi-stage: deps → build → standalone)
- **Docker Compose** frontend service updated for HMR volume mounts

### 2. API Client & Auth Layer (`frontend/src/lib/`)
- **`api-client.ts`** — fetch wrapper:
- Base URL from `NEXT_PUBLIC_API_URL`
- Auto `Authorization: Bearer <access_token>` header
- 401 interceptor: refresh token → retry → redirect on fail
- **`auth-context.tsx`** — `AuthProvider`:
- `login()`, `register()`, `logout()`, `refresh()`
- Tokens in memory + `localStorage`
- Validates session on mount via `GET /auth/me`
- Exposes `user`, `isAuthenticated`, `isLoading`
- **`AuthGuard`** — redirects to `/login` if unauthenticated

### 3. Shared UI Primitives (8 components)

| Component | Props | Notes |
|-----------|-------|-------|
| `Button` | `variant`, `loading`, `disabled`, `size` | Spinner on loading |
| `Input` | `label`, `error`, `type` | Validation error display |
| `Card` | `title?`, `action?` | Content container |
| `Table` | `columns`, `data`, `onRowClick?`, `loading?` | Sortable columns |
| `Badge` | `variant` (success/warning/error/info) | Status display |
| `Modal` | `open`, `onClose`, `title` | Overlay with close |
| `Spinner` | `size` | Loading indicator |
| `Select` | `label`, `options`, `value`, `onChange`, `error` | Dropdown |
| `Pagination` | `offset`, `limit`, `total`, `onChange` | Page nav |
| `Toast` | via `useToast` hook | Notifications |

### 4. Pages (14 routes)

| Route | Auth | Key API Calls |
|-------|------|--------------|
| `/login` | No | `POST /auth/login` |
| `/register` | No | `POST /auth/register` |
| `/` (Dashboard) | Yes | `GET /accounts`, `GET /reports/net-worth`, `GET /reports/income-vs-expenses`, `GET /transactions?limit=5` |
| `/accounts` | Yes | `GET /accounts`, `POST /accounts/{id}/sync`, `DELETE /accounts/{id}` |
| `/transactions` | Yes | `GET /transactions` (filtered + paginated), `PATCH /transactions/{id}`, `POST /transactions` |
| `/budgets` | Yes | `GET /budgets`, `POST /budgets`, `PUT /budgets/{id}`, `DELETE /budgets/{id}` |
| `/portfolio` | Yes | `GET /portfolio/holdings`, `POST /portfolio/holdings`, `PUT/DELETE /portfolio/holdings/{id}`, `GET /portfolio/summary` |
| `/reports/category-breakdown` | Yes | `GET /reports/category-breakdown` |
| `/reports/income-vs-expenses` | Yes | `GET /reports/income-vs-expenses` |
| `/reports/monthly-trends` | Yes | `GET /reports/monthly-trends` |
| `/reports/net-worth` | Yes | `GET /reports/net-worth` |
| `/connect` | Yes | `GET /connect/connections`, `DELETE /connect/connections/{id}` |
| `/connect/institutions` | Yes | `GET /connect/institutions`, `POST /connect/requisitions`, `GET /connect/requisitions/{id}` |
| `/profile` | Yes | `GET /auth/me` |

### 5. Key Pages Detail

**Dashboard** — Net worth card, income vs expenses bar chart (Recharts), account summary cards, recent transactions (compact table). Loading skeletons per section. Error boundaries isolate failing sections.

**Transactions** — Filterable table (date range, account, category, status, search text). Pagination via offset/limit. Row click opens detail modal with category override. "Add Manual" button opens create modal.

**Budgets** — Card grid with progress bars (color shift at 80%/100%). CRUD via modals. Computed `spent`, `remaining`, `progress_pct` from backend.

**Portfolio** — Summary card (market value, gain/loss, allocation donut chart via Recharts). Holdings table with computed market_value. Add/edit/delete via modals.

**Reports (4 pages)** — Each has date range/month count selector + appropriate Recharts chart (PieChart, BarChart, LineChart). Data from report endpoints.

**Bank Connect** — Institution grid with logos. Requisition flow: select institution → redirect to Nordigen → poll status → accounts created. Connections list with disconnect.

### 6. Testing Strategy

**Unit (Vitest + React Testing Library) — 35+ tests:**
- 20 component tests (Button, Input, Badge, Modal, Table, Pagination, AuthGuard, DataLoader)
- 5 hook tests (useAuth login/logout/refresh)
- 10 page/feature tests (Login, Dashboard, Transactions, Budgets)

**E2E (Playwright) — 8-10 tests:**
- Auth flow: register → login → dashboard → logout
- Transaction CRUD: list → filter → edit category
- Budget CRUD: create → verify progress → delete
- Portfolio CRUD: add holding → verify → delete

**CI Integration:**
- Frontend lint job (`npm run lint`)
- Frontend test job (`npm run test` — Vitest)
- Frontend build job (`npm run build`)

### 7. Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| State management | React Context + `useEffect` | Sufficient scope |
| HTTP client | Native `fetch` wrapper | Zero dependencies |
| Date handling | `date-fns` | Lightweight, tree-shakeable |
| Charts | Recharts | Per SRS, React-native |
| Testing | Vitest + RTL + Playwright | Fast, modern, Next.js compatible |
| Auth storage | `localStorage` + memory | Simple for MVP |
| Data fetching pattern | `DataLoader` component | Loading/empty/error/success in one place |

### 8. Implementation Order

1. Scaffold Next.js project + folder structure + Docker
2. TypeScript types (mirror all backend schemas)
3. `api-client.ts` + `auth-context.tsx` + `AuthGuard`
4. Authenticated layout (sidebar + header, responsive)
5. Shared UI primitives (10 components)
6. Auth pages (login, register)
7. Dashboard page
8. Accounts page
9. Transactions page
10. Budgets page
11. Portfolio page
12. Reports pages (4 chart pages)
13. Connect page (institutions + requisition flow)
14. Profile page
15. Frontend tests (Vitest + Playwright)
16. CI jobs for frontend
17. Manual E2E verification against running backend

### 9. Test Target: 45+ total (35 unit + 10 E2E)


## Phases

# Todos
[ ] Scaffold Next.js 15 project with TypeScript + Tailwind + App Router
[ ] Create frontend folder structure (components/ui, components/layout, lib, hooks)
[ ] Write frontend Dockerfile (multi-stage) and update docker-compose.yml
[ ] Define TypeScript types matching all backend Pydantic schemas
[ ] Build api-client.ts (fetch wrapper with auth interceptor, 401 refresh)
[ ] Build auth-context.tsx (AuthProvider, useAuth, login/register/logout/refresh)
[ ] Build AuthGuard component and authenticated route layout (sidebar + header)
[ ] Build shared UI primitives (Button, Input, Card, Table, Badge, Modal, Spinner, Select, Pagination, Toast)
[ ] Build Login and Register auth pages
[ ] Build Dashboard page (net worth, income vs expenses chart, accounts, recent transactions)
[ ] Build Accounts page (list, sync, disconnect)
[ ] Build Transactions page (filterable table, pagination, category override, manual add)
[ ] Build Budgets page (CRUD, progress bars with color thresholds)
[ ] Build Portfolio page (holdings table, summary card, allocation donut chart, CRUD)
[ ] Build Reports pages (category-breakdown, income-vs-expenses, monthly-trends, net-worth with Recharts)
[ ] Build Connect page (institution grid, requisition flow, connections list)
[ ] Build Profile page
[ ] Set up Vitest + React Testing Library, write 35+ unit tests
[ ] Set up Playwright, write 8-10 E2E tests
[ ] Add frontend CI jobs to .github/workflows/ci.yml (lint + test + build)
[ ] Manual E2E verification against running backend

Phase 1 — Foundation (tasks 1-4): Scaffold Next.js, folder structure, Docker, TypeScript types  
Phase 2 — Core Infrastructure (tasks 5-8): API client, auth context, AuthGuard, layout, UI primitives  
Phase 3 — Pages (tasks 9-17): Login/Register → Dashboard → Accounts → Transactions → Budgets → Portfolio → Reports → Connect → Profile  
Phase 4 — Quality (tasks 18-21): Vitest unit tests, Playwright E2E, CI integration, manual verification 


