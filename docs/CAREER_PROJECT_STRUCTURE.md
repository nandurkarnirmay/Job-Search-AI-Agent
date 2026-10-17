# Career Project Structure & Architectural Overview 🇮🇳

This document details the complete career project structure for the **Job Search AI Agent**, covering both **Track A (Core Foundation)** and **Track B (Advanced Production)** requirements.

---

## 🏗️ Directory Layout

```text
job-search-ai-agent/
│
├── requirements.txt            # Root dependencies for Streamlit Cloud & full project
├── streamlit_app.py            # [Track A] Interactive Streamlit Cloud deployment app
├── chatbot.py                  # [Track A] Conversational job search agent (LangChain)
├── scraper.py                  # [Track A] Standalone rate-limited Indian job scraper CLI
│
├── .streamlit/
│   └── config.toml             # Custom theme and server settings for Streamlit Cloud
│
├── backend/                    # [Track B] FastAPI Production Backend
│   ├── Dockerfile              # Container definition for API deployment
│   ├── requirements.txt        # Backend Python dependencies
│   ├── requirements-dev.txt    # Testing & linting tools (pytest, ruff)
│   ├── pyproject.toml          # Ruff and tool configs
│   ├── .env.example            # Environment variables template
│   │
│   ├── app/
│   │   ├── main.py             # FastAPI entrypoint, CORS, routes & lifespan
│   │   ├── config.py           # Pydantic BaseSettings with .env validation
│   │   ├── db.py               # SQLAlchemy database session & engine
│   │   ├── models.py           # SQLAlchemy User, Profile, and SearchLog models
│   │   ├── schemas.py          # Pydantic API request & response schemas
│   │   ├── domain.py           # Core domain models (JobListing, SearchParams)
│   │   ├── deps.py             # Dependency injection (Auth, DB, rate limiter)
│   │   ├── security.py         # JWT tokens, bcrypt password hashing
│   │   ├── cache.py            # Redis cache with in-memory fallback
│   │   ├── ratelimit.py        # Per-client sliding window rate limiter
│   │   ├── monitoring.py       # Prometheus metrics, JSON structured logging
│   │   ├── errors.py           # Standardized error codes and error handlers
│   │   │
│   │   ├── agent/
│   │   │   ├── graph.py        # [Track B] LangGraph state graph workflow
│   │   │   └── llm.py          # Google Gemini LLM factory with structured output
│   │   │
│   │   ├── routers/
│   │   │   ├── auth.py         # Registration, login, JWT issuance, account deletion
│   │   │   ├── profile.py      # Career profile management (skills, cities, LPA)
│   │   │   ├── jobs.py         # Filtered job search endpoint with caching
│   │   │   ├── chat.py         # Conversational agent query endpoint
│   │   │   ├── health.py       # Health check (DB, Redis, upstream sources)
│   │   │   └── stats.py        # Admin search analytics & engagement metrics
│   │   │
│   │   ├── services/
│   │   │   ├── search_service.py # Orchestrates cache, aggregator, filtering & logging
│   │   │   ├── query_parser.py   # Indian market rule-based NLP query parser
│   │   │   └── filters.py        # City alias, experience, salary LPA, notice filters
│   │   │
│   │   └── sources/
│   │       ├── base.py         # Abstract JobSource with circuit breaker & retries
│   │       ├── aggregator.py   # Parallel multi-source executor & deduplicator
│   │       ├── scraper.py      # [Track A+B] Requests + BeautifulSoup scraper
│   │       ├── adzuna.py       # Adzuna India API client
│   │       ├── jsearch.py      # JSearch API client
│   │       └── normalize.py    # Text normalizers (Rupees to LPA, notice, dedupe)
│   │
│   └── tests/                  # Automated Pytest Suite
│       ├── conftest.py         # Test fixtures, SQLite in-memory DB, fake sources
│       ├── test_auth_profile.py# JWT auth and profile lifecycle tests
│       ├── test_parsing.py     # Indian NLP parsing & text normalization tests
│       ├── test_search.py      # Search, filter, cache, and rate limit tests
│       ├── test_sources.py     # Source resilience and circuit breaker tests
│       └── test_scraper.py     # Indian scraper and rate limiter tests
│
├── frontend/                   # [Track B] Next.js 14 App Router UI
│   ├── app/
│   │   ├── page.tsx            # Modern landing page
│   │   ├── search/page.tsx     # Chat & Filter search interfaces
│   │   ├── profile/page.tsx    # Candidate career profile form
│   │   ├── login/page.tsx      # User login form
│   │   └── register/page.tsx   # User registration form
│   ├── components/             # Reusable UI components (JobCard, Nav, AuthForm)
│   └── lib/api.ts              # Fetch client with JWT handling and error types
│
├── docs/                       # Project Documentation
│   ├── ARCHITECTURE.md         # System architecture and data flow
│   ├── PLAN.md                 # Project roadmap and milestones
│   ├── DEPLOY.md               # Render and Vercel deployment guide
│   ├── STREAMLIT_DEPLOY.md     # [Track A] Streamlit Cloud deployment guide
│   ├── DEMO_SCRIPT_2MIN.md     # [Track A] 2-minute video walkthrough script
│   └── CAREER_PROJECT_STRUCTURE.md # Career project structure guide
│
├── .github/
│   └── workflows/
│       └── ci.yml              # CI/CD pipeline (lint, SQLite/Postgres tests, Next.js build)
│
├── docker-compose.yml          # Local multi-container stack (Postgres + Redis + API)
└── render.yaml                 # Infrastructure-as-code for Render deployment
```

---

## ⚖️ Track Comparison: Track A vs. Track B

| Feature | Track A (Core Foundation) | Track B (Advanced Production) |
|---|---|---|
| **Primary Interface** | Streamlit Cloud Web App (`streamlit_app.py`) | Next.js 14 Web App + FastAPI Backend |
| **Agent Engine** | LangChain conversational chatbot (`chatbot.py`) | LangGraph State Graph with fallback (`backend/app/agent/graph.py`) |
| **Job Sources** | Indeed India & Naukri Scraper with polite rate limiter | Parallel Aggregator: Scraper + Adzuna India + JSearch |
| **Data Normalization** | Salary to LPA, Experience to years, Notice period | Full schema normalization + deduplication hashing |
| **Filtering** | City, Experience (Freshers to 5+ yrs), Salary LPA, Notice period | Pre-cache and post-cache ranking with stretch tolerance |
| **Authentication** | Session-based / standalone demo access | Full JWT authentication with bcrypt password hashing |
| **Persistence** | In-memory session state & CSV/JSON export | PostgreSQL (Neon) with SQLAlchemy ORM + Redis (Upstash) |
| **Resilience** | Token interval rate limiter with randomized jitter | Circuit Breaker + exponential retries + 429 client limiter |
| **Monitoring** | Live Scraper Inspector metrics in UI | Prometheus `/metrics`, structured JSON logs, `/stats/search` |
| **CI / CD** | Deployable to Streamlit Community Cloud | GitHub Actions (SQLite, Postgres 16, Next.js typecheck & build) |
