graph TD
    %% Infrastructure & CI/CD Subgraph
    subgraph Infra ["Infrastructure & CI/CD"]
        GHA["GitHub Actions <br> CI: lint · test · build <br> CD: deploy on merge"]
        Railway["Railway <br> Production deployment <br> Auto-scaling"]
        Docker["Docker · Docker Compose <br> Local dev environment"]
    end

    %% Client Layer Subgraph
    subgraph Client ["Client Layer"]
        PWA["PWA / Mobile"]
        Browser["Browser <br> Next.js 15 - TypeScript <br> Tailwind - Recharts"]
    end

    %% CDN / Edge Subgraph
    subgraph CDN_Layer ["CDN / Edge"]
        Vercel["Vercel Edge Network <br> Static assets - SSR cache"]
    end

    %% API Gateway Subgraph
    subgraph Gateway ["API Gateway"]
        CORS["CORS Middleware <br> Rate Limiter <br> 100 req/min per user"]
        FastAPI["FastAPI - Uvicorn <br> Python 3.12 <br> REST + WebSocket"]
    end

    %% Async Workers Subgraph
    subgraph Async ["Async Workers"]
        Celery["Celery Worker <br> Task Queue"]
        Tasks["Tasks <br> • PDF report generation <br> • Budget alert notifications <br> • Transaction sync <br> • ML re-training"]
    end

    %% Application Modules Subgraph
    subgraph Modules ["Application Modules"]
        AI_Adv["AI Advisor <br> Claude API <br> Context aware chat"]
        Fin_Mod["Finance Module <br> Transactions <br> Budgets - Portfolio"]
        Rep_Mod["Report Module <br> PDF - CSV <br> ReportLab"]
        ML_Mod["ML Module <br> scikit-learn <br> Category Classifier"]
        Auth_Mod["Auth Module <br> JWT - OAuth2 <br> passlib - python jose"]
    end

    %% External Services Subgraph
    subgraph External ["External Services"]
        Claude["Anthropic Claude API <br> Financial Advisor <br> Context-aware responses"]
        Alpha["Alpha Vantage <br> Market Data API <br> Stocks - Crypto prices"]
        SMTP["SMTP / SendGrid <br> Email notifications <br> Report delivery"]
        Plaid["Plaid / Nordigen <br> Open Banking API <br> PSD2 - EU Compliant"]
    end

    %% Data Layer Subgraph
    subgraph Data ["Data Layer"]
        Redis["Redis 7 <br> Cache - Sessions <br> Rate limit counters <br> WebSocket pub/sub"]
        MSSQL["MS SQL Server 2022 <br> Primary Database <br> users - accounts <br> transactions - budgets <br> portfolio - categories"]
    end

    %% Akışlar ve Bağlantılar
    GHA --> Railway
    GHA --> Docker
    Railway --> FastAPI
    Docker --> FastAPI

    PWA -->|HTTPS| Vercel
    Browser -->|"HTTPS / WebSocket"| Vercel
    Vercel -->|Proxy| FastAPI

    CORS -.->|wraps| FastAPI
    
    FastAPI -->|enqueue jobs| Celery
    Celery --- Tasks
    Tasks -->|send email| SMTP

    FastAPI --- AI_Adv
    FastAPI --- Fin_Mod
    FastAPI --- Rep_Mod
    FastAPI --- ML_Mod
    FastAPI --- Auth_Mod

    AI_Adv -->|LLM inference| Claude
    Fin_Mod -->|price fetch| Alpha
    Plaid -->|bank data| Fin_Mod

    FastAPI --> Redis
    FastAPI --> MSSQL
    Fin_Mod --> Redis
    Fin_Mod --> MSSQL
    Tasks --> Redis
    Tasks --> MSSQL
    ML_Mod --> MSSQL
    Auth_Mod --> MSSQL
    Rep_Mod --> MSSQL
