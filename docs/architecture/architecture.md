graph TD

    %% ── Infrastructure & CI/CD ─────────────────────────────────────────────
    subgraph Infra ["Infrastructure & CI/CD"]
        GHA["GitHub Actions\nCI: ruff · pytest · eslint · vitest\nCD: deploy on merge to main"]
        Docker["Docker · Docker Compose\nLocal dev — 6-service stack"]
        Railway["Railway (planned)\nProduction deployment"]
    end

    %% ── Client Layer ───────────────────────────────────────────────────────
    subgraph Client ["Client Layer"]
        Browser["Browser\nNext.js 15 · TypeScript\nTailwind CSS · Recharts\nreact-plaid-link"]
    end

    %% ── API Gateway ────────────────────────────────────────────────────────
    subgraph Gateway ["API Gateway  ·  FastAPI 0.115 · Uvicorn · Python 3.12"]
        CORS["CORS Middleware\nAllowlist origins"]
        RateLimit["Rate Limiter\n100 req / min per user"]
        FastAPI["REST  /api/v1/*\nWebSocket  /api/v1/ws\nHealth  /health\nOpenAPI  /docs"]
    end

    %% ── Application Modules ────────────────────────────────────────────────
    subgraph Modules ["Application Modules  (app/services/)"]
        Auth["Auth Service\nJWT access + refresh tokens\nbcrypt · python-jose\nRBAC: user / admin"]
        Connect["Connect Service\nPlaid link_token create\npublic_token exchange\nFernet token encryption"]
        TxnSvc["Transaction Service\ndedupe hash (SHA-256)\ncategory override\nfilter / paginate"]
        BudgetSvc["Budget Service\nmonthly progress calc\n80% threshold alert"]
        PortfolioSvc["Portfolio Service\nHolding CRUD\nP&L · allocation %"]
        ReportSvc["Report Service\nmonthly summary JSON\nCSV generation"]
        ChatSvc["Chat Service\nfinancial context builder\nGroq API (OpenAI-compat)\npersist chat_message"]
        ExportSvc["Export Service\nPDF · CSV via Celery\nstatus polling"]
        NotifSvc["Notification Service\ncreate · mark read\nWebSocket push"]
    end

    %% ── ML Module ──────────────────────────────────────────────────────────
    subgraph ML ["ML Module  (app/ml/)"]
        Rules["Rule Engine\ncompiled regex\nPolish / EU merchants"]
        Classifier["TransactionClassifier\nTF-IDF + Logistic Regression\nscikit-learn 1.5\ncalibrated probabilities"]
    end

    %% ── Async Workers ──────────────────────────────────────────────────────
    subgraph Async ["Async Workers  (Celery 5.4 + Redis broker)"]
        Beat["Celery Beat\nSync schedule\nevery 4 h"]
        Worker["Celery Worker\ntask_acks_late=True\nprefetch×4"]
        T1["ingestion.sync_account_transactions\nPlaid /transactions/sync\ndedupe · insert · classify"]
        T2["ingestion.sync_all_due_connections\nfan-out per active connection"]
        T3["classification.reclassify_transactions\nbatch ML re-run"]
        T4["export.generate_pdf_report\nReportLab 4.2"]
        T5["budget_alert\ncreate Notification\nWebSocket push via Redis"]
    end

    %% ── Data Layer ─────────────────────────────────────────────────────────
    subgraph Data ["Data Layer"]
        MSSQL["MS SQL Server 2022\nSQLAlchemy 2.0 · Alembic\n11 tables · UUID PKs\nuser_account · bank_connection\naccount · transaction · category\nbudget · holding · notification\nchat_message · refresh_token · export"]
        Redis["Redis 7\nCelery broker + result backend\nmarket price cache (5 min TTL)\nWebSocket pub/sub bridge"]
    end

    %% ── External Services ──────────────────────────────────────────────────
    subgraph External ["External Services"]
        Plaid["Plaid API\nOpen Banking (AISP / PSD2)\nlink_token · public_token\n/accounts/get\n/transactions/sync\nCountries: US GB NL PL"]
        Groq["Groq API\nOpenAI-compatible\nllama-3.3-70b-versatile\nAI financial advisor"]
        AlphaV["Alpha Vantage\nReal-time market prices\nStocks · ETFs · Crypto"]
    end

    %% ── CI/CD flows ────────────────────────────────────────────────────────
    GHA -->|"on push / PR"| Docker
    GHA -->|"on merge"| Railway
    Railway -->|"runs"| FastAPI
    Docker -->|"runs"| FastAPI

    %% ── Client → Gateway ───────────────────────────────────────────────────
    Browser -->|"HTTPS REST /api/v1/*"| FastAPI
    Browser -->|"WSS /api/v1/ws?token=..."| FastAPI

    %% ── Gateway internals ──────────────────────────────────────────────────
    CORS -.->|"wraps"| FastAPI
    RateLimit -.->|"wraps"| FastAPI

    %% ── Gateway → Modules ──────────────────────────────────────────────────
    FastAPI --- Auth
    FastAPI --- Connect
    FastAPI --- TxnSvc
    FastAPI --- BudgetSvc
    FastAPI --- PortfolioSvc
    FastAPI --- ReportSvc
    FastAPI --- ChatSvc
    FastAPI --- ExportSvc
    FastAPI --- NotifSvc

    %% ── Plaid Link flow ────────────────────────────────────────────────────
    Connect -->|"1 link_token"| Plaid
    Browser -->|"2 Plaid Link SDK (iframe)"| Plaid
    Browser -->|"3 public_token POST"| Connect
    Connect -->|"4 exchange → access_token (encrypted)"| MSSQL

    %% ── ML pipeline ────────────────────────────────────────────────────────
    TxnSvc -->|"classify"| Rules
    Rules -->|"no match → ML"| Classifier
    Classifier -->|"category + confidence"| TxnSvc

    %% ── Celery flows ───────────────────────────────────────────────────────
    Beat -->|"every 4 h"| T2
    T2 -->|"fan-out"| T1
    FastAPI -->|"enqueue"| T1
    FastAPI -->|"enqueue"| T4
    T1 -->|"classify"| Rules
    T1 -->|"80% budget check"| T5
    T3 -->|"batch classify"| Classifier
    T4 -->|"ReportLab PDF"| ExportSvc
    T5 -->|"push"| NotifSvc
    Worker --- T1
    Worker --- T2
    Worker --- T3
    Worker --- T4
    Worker --- T5

    %% ── External API calls ─────────────────────────────────────────────────
    T1 -->|"transactions/sync"| Plaid
    ChatSvc -->|"chat/completions"| Groq
    PortfolioSvc -->|"price fetch"| AlphaV
    AlphaV -->|"cached 5 min"| Redis

    %% ── Data access ────────────────────────────────────────────────────────
    Auth --- MSSQL
    TxnSvc --- MSSQL
    BudgetSvc --- MSSQL
    PortfolioSvc --- MSSQL
    ReportSvc --- MSSQL
    ChatSvc --- MSSQL
    ExportSvc --- MSSQL
    NotifSvc --- MSSQL
    Connect --- MSSQL
    T1 --- MSSQL
    T4 --- MSSQL
    FastAPI --- Redis
    T1 --- Redis
    T5 --- Redis
