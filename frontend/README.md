# WealthFlow Frontend

Next.js 15 + TypeScript frontend for the WealthFlow personal finance platform.

[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-blue)](https://www.typescriptlang.org/)
[![Next.js](https://img.shields.io/badge/Next.js-15-black)](https://nextjs.org/)
[![Tests](https://img.shields.io/badge/Tests-40%20unit%20%7C%2015%20E2E-green)]()

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Framework | Next.js 15 (App Router) |
| Language | TypeScript (strict) |
| Styling | Tailwind CSS v4 |
| Charts | Recharts |
| HTTP Client | Native `fetch` wrapper |
| State Mgmt | React Context + hooks |
| Date Handling | `date-fns` |
| Testing | Vitest + RTL + Playwright |

## Pages (14 routes)

| Route | Auth | Description |
|-------|------|-------------|
| `/login` | No | Login form |
| `/register` | No | Registration form |
| `/` (Dashboard) | Yes | Net worth, income/expenses, recent transactions |
| `/accounts` | Yes | Connected bank accounts |
| `/transactions` | Yes | Filterable transaction list with pagination |
| `/budgets` | Yes | Budget CRUD with progress bars |
| `/portfolio` | Yes | Holdings table + summary + allocation chart |
| `/reports/category-breakdown` | Yes | Spending by category (pie chart) |
| `/reports/income-vs-expenses` | Yes | Monthly income vs expenses (bar chart) |
| `/reports/monthly-trends` | Yes | Trends over time (line chart) |
| `/reports/net-worth` | Yes | Net worth over time (line chart) |
| `/connect` | Yes | Bank connection management |
| `/connect/institutions` | Yes | Institution browser + requisition flow |
| `/profile` | Yes | User profile |

## Shared UI Components

| Component | Category | Description |
|-----------|----------|-------------|
| `Button` | ui | Variants, loading spinner, sizes |
| `Input` | ui | Label, validation error display |
| `Card` | ui | Content container with optional title/action |
| `Table` | ui | Sortable columns, loading state, row click |
| `Badge` | ui | Status display (success/warning/error/info) |
| `Modal` | ui | Overlay with close button |
| `Spinner` | ui | Loading indicator |
| `Select` | ui | Dropdown with label and error |
| `Pagination` | ui | Offset/limit page navigation |
| `Toast` | ui | Notification via `useToast` hook |
| `Sidebar` | layout | Responsive sidebar with mobile overlay |
| `Header` | layout | Top navigation bar |
| `AuthGuard` | layout | Redirects to `/login` if unauthenticated |

## Scripts

```bash
npm run dev          # Development server (HMR)
npm run build        # Production build (type-check + compile)
npm start            # Start production server
npm test             # Run Vitest unit tests
npm run test:ui      # Vitest UI mode
npm run e2e          # Run Playwright E2E tests
npm run lint         # ESLint
```

## Docker

```bash
# Build
docker build -t wealthflow-frontend .

# Run with Docker Compose (from project root)
docker compose up frontend
```

## Project Structure

```
frontend/src/
├── app/
│   ├── (auth)/            # login, register
│   ├── (dashboard)/       # authenticated layout with sidebar
│   │   ├── page.tsx       # dashboard home
│   │   ├── accounts/
│   │   ├── transactions/
│   │   ├── budgets/
│   │   ├── portfolio/
│   │   ├── reports/
│   │   └── connect/
│   └── layout.tsx
├── components/
│   ├── ui/                # Button, Input, Card, Table, Badge, Modal, etc.
│   ├── layout/            # Sidebar, Header, AuthGuard
│   └── charts/            # Recharts wrappers
├── lib/
│   ├── api-client.ts      # Fetch wrapper with auth interceptor
│   ├── auth-context.tsx   # AuthProvider + useAuth hook
│   └── types.ts           # TypeScript types matching backend schemas
└── hooks/
```

## Related

- [Backend API Docs](http://localhost:8000/docs) (when running)
- [Root Project README](../README.md)
- [Sprint 3 Summary](../docs/sprint-3.md)