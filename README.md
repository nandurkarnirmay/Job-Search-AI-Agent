# Job Search AI Agent 🇮🇳

An AI-powered career platform specifically engineered for the **Indian job market**. Ask in plain English (*"remote Python jobs in Bengaluru above 8 LPA for a fresher"*) and the agent converts your prompt into structured searches across Indian job portals, filtered by city, experience, salary in LPA, work mode, and notice period.

---

## ✅ Milestones & Project Checklists

### Track A Checklist (Core Foundation)
- [x] **Create GitHub repo with career project structure** (Modular `backend/`, `frontend/`, `docs/`, `streamlit_app.py`, `chatbot.py`, `scraper.py`)
- [x] **Set up development environment** (`Python 3.12`, `requests`, `beautifulsoup4`, `langchain`, `pydantic`)
- [x] **Build basic job search chatbot with Indian job sites** (LangChain conversational agent with Gemini & resilient rules fallback)
- [x] **Implement simple job listing scraper** (Indeed India & Naukri parser with thread-safe rate limiter and jitter)
- [x] **Add job filtering by location, experience, salary** (Indian cities, freshers/years exp, salary in LPA, work mode, notice period)
- [x] **Deploy basic version on Streamlit Cloud** ([Streamlit Cloud Guide](docs/STREAMLIT_DEPLOY.md) · Single-click deployable `streamlit_app.py`)
- [x] **Record 2-minute demo showing job search queries** ([2-Minute Video Script & Storyboard](docs/DEMO_SCRIPT_2MIN.md))
- [x] **Milestone: Working deployed demo with Indian job listings**

### Track B Checklist (Advanced Production)
- [x] **All Track A requirements plus:**
- [x] **Set up advanced environment** (LangGraph workflow, PostgreSQL with Neon/Docker, Redis with Upstash, FastAPI)
- [x] **Implement user authentication and profile management** (JWT auth, bcrypt password hashing, career profiles with preferred cities, skills, expected LPA, notice period)
- [x] **Add comprehensive error handling for API failures and rate limits** (Circuit breaker, per-source retries with backoff, sliding window client rate limiter, uniform error schema)
- [x] **Set up monitoring for job search performance and user engagement** (Prometheus `/metrics`, structured JSON logs with `x-request-id`, `/health`, `/stats/search` admin analytics)
- [x] **Create CI/CD pipeline with automated testing** (GitHub Actions running ruff linting, SQLite & Postgres test suites, Next.js build)

---

## 🚀 Quick Start

### Option 1: Track A – Streamlit App (Fastest & Zero Setup)
Run the interactive Streamlit dashboard locally or deploy with one click to Streamlit Cloud:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Launch Streamlit UI
streamlit run streamlit_app.py
```
Open [http://localhost:8501](http://localhost:8501) to explore:
- **💬 AI Career Assistant:** Natural language job search with conversational memory.
- **🔍 Filtered Job Explorer:** Multi-criteria filtering by city, experience, LPA salary, work mode, notice period with CSV/JSON export.
- **⚡ Scraper & Rate Limiter Inspector:** Live scraper status, polite request intervals, and latency metrics.

👉 **Deploy to Cloud:** Follow the [Streamlit Cloud Deployment Guide](docs/STREAMLIT_DEPLOY.md).

---

### Option 2: Track A – Standalone Scraper CLI
Test the rate-limited Indian job scraper directly from your terminal:

```bash
python scraper.py --keywords "python developer" --city "Bengaluru" --limit 5
```

---

### Option 3: Track B – Full Production Stack (FastAPI + Postgres + Redis + Next.js)

```bash
# 1. Start Postgres + Redis + FastAPI Backend
cp backend/.env.example backend/.env
docker compose up --build
# API running on http://localhost:8000/docs

# 2. Start Next.js Frontend
cd frontend
cp .env.example .env.local
npm install
npm run dev
# Frontend running on http://localhost:3000
```

Without Docker:
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate | Unix: source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

---

## 🧪 Automated Testing & CI/CD

Run the test suite covering parsing, filtering, rate limiting, and auth:

```bash
cd backend
pytest -v
ruff check .
```

Our `.github/workflows/ci.yml` pipeline automatically tests every pull request and push:
1. **Linting:** Ruff code style and import verification.
2. **Backend Tests:** Dual execution on SQLite (in-memory) and real PostgreSQL 16 Alpine.
3. **Frontend Tests:** Next.js type-checking and production bundle compilation.
4. **Continuous Deployment:** Webhook triggers automated deployment to Render on `main`.

---

## 📊 Core Architecture & Capabilities

```text
┌──────────────────────────────────────────────────────────────────┐
│                           CLIENT TIER                            │
│   Streamlit Cloud App (Track A)   /   Next.js 14 Web App (Track B)│
└────────────────┬─────────────────────────────────┬───────────────┘
                 │                                 │
                 ▼                                 ▼
┌────────────────────────────────┐   ┌─────────────────────────────┐
│    Track A (Core Chatbot)      │   │   Track B (FastAPI Gateway) │
│  • LangChain Gemini Agent      │   │   • JWT Auth & Profiles     │
│  • Rate-limited Scraper Engine │   │   • LangGraph State Graph   │
│  • Multi-criteria Filter       │   │   • Prometheus /metrics     │
└────────────────┬───────────────┘   └─────────────┬───────────────┘
                 │                                 │
                 ▼                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│                    AGGREGATED DATA SOURCES                       │
│  • Indian Job Scraper (Indeed IN / Naukri with Rate Limiting)    │
│  • Adzuna India API (Parallel executor + circuit breaker)        │
│  • JSearch Aggregator API (Monthly to LPA normalization)         │
└──────────────────────────────────────────────────────────────────┘
```

- **Salary in LPA:** Parses strings like *"₹8,00,000 - ₹12,00,000 a year"* or *"10-15 Lacs P.A."* into standard Indian Lakhs Per Annum.
- **Experience Normalization:** Detects *"Freshers"*, *"Entry-level"*, or ranges like *"2-4 years"*.
- **Notice Period Handling:** Identifies immediate joiners (`notice_period_days = 0`) vs. 30, 60, or 90 days.
- **Circuit Breaker & Resilience:** Upstream failures fail gracefully without taking down the search; partial results are merged seamlessly.
- **Rate Limiting:** Token interval throttling with randomized jitter (0.2s - 0.8s) guarantees polite crawling.

---

## 📖 Documentation Index

- [docs/DEMO_SCRIPT_2MIN.md](docs/DEMO_SCRIPT_2MIN.md): Second-by-second 2-minute video walkthrough script.
- [docs/STREAMLIT_DEPLOY.md](docs/STREAMLIT_DEPLOY.md): Guide for deploying to Streamlit Community Cloud.
- [docs/CAREER_PROJECT_STRUCTURE.md](docs/CAREER_PROJECT_STRUCTURE.md): Detailed architectural breakdown and file tour.
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): Track B micro-service design, data models, and caching strategy.
- [docs/PLAN.md](docs/PLAN.md): Multi-week roadmap and milestone checklist.
- [docs/DEPLOY.md](docs/DEPLOY.md): Render and Vercel production hosting guidelines.
