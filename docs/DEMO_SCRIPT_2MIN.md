# 2-Minute Demo Video Script & Storyboard 🎬

Use this second-by-second script to record your **2-minute video demonstration** showcasing the **Job Search AI Agent 🇮🇳**.

---

## ⏱️ Video Breakdown (Total: 120 Seconds)

| Timestamp | Phase | What's on Screen | Voiceover / Action |
|---|---|---|---|
| **0:00 – 0:20** | **Introduction & Problem Statement** | Streamlit or Next.js Homepage with title and badges visible | Introduce yourself and the problem: searching Indian tech jobs across fragmented portals with non-standard salary formats and tricky filters. |
| **0:20 – 0:50** | **Natural Language Search Queries** | `💬 AI Career Assistant` tab | Type a plain English query: *"Remote Python developer jobs in Bengaluru above 8 LPA for a fresher"*. Show the agent parsing intent and returning cards. |
| **0:50 – 1:20** | **Multi-Criteria Job Filtering & Scraper** | `🔍 Filtered Job Explorer` & `⚡ Scraper Inspector` | Demonstrate filter controls (Location: Bengaluru, Min Salary: 10 LPA, Fresher, Work Mode: Hybrid). Switch to Scraper Inspector to show rate-limited crawling of Indeed India & Naukri. |
| **1:20 – 1:45** | **Track B Advanced Backend (FastAPI + LangGraph + Auth)** | Swagger UI (`/docs`) & Next.js UI | Show JWT authentication, profile management (preferred cities, skills), LangGraph state graph execution, and Prometheus `/metrics`. |
| **1:45 – 2:00** | **Deployment & Summary** | Streamlit Cloud / Render live URL + GitHub Actions CI/CD | Highlight the zero-failure deployment, circuit breaker resilience, and automated testing pipeline. Conclude with impact. |

---

## 🎙️ Step-by-Step Recording Walkthrough

### Part 1: Introduction (0:00 – 0:20)
- **Screen:** Open `streamlit_app.py` or the deployed Streamlit Cloud URL.
- **What to say:**
  > *"Hello! Today I'm excited to present our Job Search AI Agent for the Indian job market. Navigating Indian tech jobs often means dealing with fragmented listings, non-standard CTC formats, notice periods, and conflicting experience requirements. We built an AI career assistant that turns plain English questions into verified job openings."*

### Part 2: Natural Language AI Chatbot (0:20 – 0:50)
- **Screen:** Navigate to **💬 AI Career Assistant** tab.
- **Action:** Click one of the quick prompt buttons or paste:
  ```text
  Remote Python developer jobs in Bengaluru above 8 LPA for a fresher
  ```
- **What to say:**
  > *"Notice how I can ask in plain English: 'Remote Python developer jobs in Bengaluru above 8 LPA for a fresher'. Our AI agent analyzes the message, understands the 8 LPA salary threshold, identifies Bengaluru and remote work mode, and flags that the candidate is a fresher. It instantly surfaces matching openings from top tech companies like Swiggy, Razorpay, and CRED with direct apply links."*
- **Action:** Expand the **🛠️ Understood Filters** accordion to show the parsed fields.

### Part 3: Live Scraper & Granular Filtering (0:50 – 1:20)
- **Screen:** Switch to **🔍 Filtered Job Explorer** tab.
- **Action:**
  1. Set Role: `React Developer`
  2. City: `Bengaluru`
  3. Min Salary: `12 LPA`
  4. Work Mode: `Remote`
  5. Hit **Search Indian Jobs**.
- **What to say:**
  > *"In addition to conversational search, candidates can use granular multi-criteria filters. We extract Indian-specific metrics such as LPA salary brackets, experience in years, and notice periods—even distinguishing immediate joiners from 30 or 60-day notice candidates. Users can also export all matches to CSV or JSON with a single click."*
- **Screen:** Switch to **⚡ Scraper & Rate Limiter Inspector** tab.
- **Action:** Show the live metrics: Total Requests and Throttled Time. Click **Run Rate-Limited Scrape Now**.
  > *"Under the hood, our scraper uses BeautifulSoup and Requests with a thread-safe rate limiter. It enforces polite request intervals with randomized jitter to prevent IP bans from sites like Indeed India and Naukri."*

### Part 4: Track B Advanced Architecture (1:20 – 1:45)
- **Screen:** Switch to browser tab with FastAPI Swagger docs (`http://localhost:8000/docs`) or Next.js app.
- **Action:**
  1. Scroll through `/auth/login`, `/me/profile`, `/jobs/search`, `/chat`, and `/metrics`.
  2. Show `/health` returning `{"database": true, "cache": {"backend": "..."}}`.
- **What to say:**
  > *"For Track B, we scaled this into a production-grade micro-architecture powered by FastAPI, LangGraph, PostgreSQL, and Redis caching. Users can register, log in with JWT, and save career profiles. Queries are protected by circuit breakers and retries with backoff, while Prometheus tracks request latencies and search analytics."*

### Part 5: CI/CD & Wrap-up (1:45 – 2:00)
- **Screen:** Show GitHub repository `.github/workflows/ci.yml` with green checkmark or Streamlit Cloud URL.
- **What to say:**
  > *"Our pipeline is fully automated with GitHub Actions running ruff linting, SQLite & Postgres test suites, and frontend verification on every commit. Both Track A and Track B are fully implemented and deployed. Thank you!"*

---

## 💡 Quick Tips for Recording
1. **Resolution:** 1080p (1920x1080) at 30 or 60 FPS.
2. **Tools:** OBS Studio, Loom, or Windows Game Bar (`Win + G`).
3. **Audio:** Use a clean microphone or headset; minimize background noise.
4. **Pacing:** Speak at a steady, enthusiastic pace. Follow the timing marks closely.
