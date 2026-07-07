# WealthFlow Documentation

[![CI](https://github.com/MuzafferDemirhan/WealthFlow/actions/workflows/ci.yml/badge.svg)](https://github.com/MuzafferDemirhan/WealthFlow/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](../LICENSE)
[![Sprints](https://img.shields.io/badge/Sprints-0--3%20complete%2C%204%20active-yellow)]()
[![SRS](https://img.shields.io/badge/SRS-v1.1.0-blue)](./SRS/SRS.md)

Central hub for all WealthFlow project documentation.

---

## Sprint Timeline

```mermaid
gantt
    title WealthFlow Sprint Timeline
    dateFormat  YYYY-MM-DD
    axisFormat  %b %d

    section Sprint 0
    Project Scaffolding     :done, s0, 2026-06-01, 7d
    Docker + DB + CI/CD     :done, 2026-06-03, 5d

    section Sprint 1
    Backend Core            :done, s1, 2026-06-08, 14d
    Auth + CRUD + Tests     :done, 2026-06-10, 12d

    section Sprint 2
    Open Banking + ML       :done, s2, 2026-06-22, 14d
    Portfolio + Reports     :done, 2026-06-25, 11d

    section Sprint 3
    Frontend Dashboard      :done, s3, 2026-07-06, 14d
    14 Pages + 55 Tests     :done, 2026-07-08, 12d

    section Sprint 4
    AI + Reports + Deploy   :active, s4, 2026-07-20, 14d
```

---

## Quick Navigation

| Document | Description | Status |
|----------|-------------|--------|
| [SRS](./SRS/SRS.md) | Software Requirements Specification | ✅ v1.1.0 |
| [Architecture](./architecture/architecture.md) | System architecture diagram (Mermaid) | ✅ |
| [ER Diagram](./ER%20diagram/erd.md) | Database entity relationship diagram (Mermaid) | ✅ |
| [sprint-0.md](./sprint-0.md) | Project scaffolding, Docker, CI/CD | ✅ |
| [sprint-1.md](./sprint-1.md) | Backend core: auth, accounts, budgets, transactions | ✅ |
| [sprint-2.md](./sprint-2.md) | Open Banking, ML classifier, portfolio, reports | ✅ |
| [sprint-3.md](./sprint-3.md) | Next.js frontend, 14 pages, 55 tests | ✅ |
| [sprint-4.md](./sprint-4.md) | AI chatbot (Ollama), export, WebSockets, Railway deploy | 🔄 Active |

---

## Document Relationships

```mermaid
graph LR
    SRS[SRS] --> s0[Sprint 0]
    SRS --> s1[Sprint 1]
    SRS --> s2[Sprint 2]
    SRS --> s3[Sprint 3]
    SRS --> s4[Sprint 4]

    s0 --> ARCH[Architecture]
    s0 --> ERD[ER Diagram]

    s1 --> s2
    s2 --> s3
    s3 --> s4

    ARCH -.->|references| s2
    ERD -.->|references| s0

    click SRS "./SRS/SRS.md"
    click s0 "./sprint-0.md"
    click s1 "./sprint-1.md"
    click s2 "./sprint-2.md"
    click s3 "./sprint-3.md"
    click s4 "./sprint-4.md"
    click ARCH "./architecture/architecture.md"
    click ERD "./ER%20diagram/erd.md"
```

---

## How to Use This Documentation

1. **Start here** — get an overview of the project and its sprint structure
2. **Read the SRS** — understand requirements, scope, and tech stack
3. **Follow sprint docs** — each sprint builds on the previous one
4. **View architecture/ERD** — for system and database design details

---

## Related

- [Root Project README](../README.md)
- [Frontend README](../frontend/README.md)
