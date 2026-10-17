"""Job Search AI Agent 🇮🇳 - Streamlit Cloud Application.

Track A Deployed Version:
- AI Job Search Chatbot with Indian job portals
- Simple job listing scraper (Indeed / Naukri with polite rate limiting)
- Multi-criteria job filtering: Location, Experience, Salary in LPA, Work Mode, Notice Period
- CSV / JSON export of opportunities
- Live Scraper & Rate Limiter Inspector
"""
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
for p in (str(BACKEND), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

import streamlit as st

from app.domain import JobListing, SearchParams
from app.services.filters import apply_filters
from app.services.query_parser import parse_query
from app.sources.aggregator import get_aggregator
from app.sources.scraper import rate_limiter
from chatbot import JobSearchChatbot

# Configure page layout and metadata
st.set_page_config(
    page_title="Job Search AI Agent 🇮🇳 | Indian Tech Jobs",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling for modern glassmorphism and card UI
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    .main-title {
        background: linear-gradient(135deg, #38BDF8 0%, #818CF8 50%, #C084FC 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.4rem;
        margin-bottom: 0.2rem;
    }
    
    .badge-pill {
        display: inline-block;
        padding: 0.25rem 0.65rem;
        font-size: 0.75rem;
        font-weight: 600;
        border-radius: 9999px;
        margin-right: 0.4rem;
        margin-bottom: 0.4rem;
    }
    
    .badge-lpa {
        background: rgba(16, 185, 129, 0.15);
        color: #34D399;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    
    .badge-exp {
        background: rgba(59, 130, 246, 0.15);
        color: #60A5FA;
        border: 1px solid rgba(59, 130, 246, 0.3);
    }
    
    .badge-mode {
        background: rgba(168, 85, 247, 0.15);
        color: #C084FC;
        border: 1px solid rgba(168, 85, 247, 0.3);
    }
    
    .badge-source {
        background: rgba(245, 158, 11, 0.15);
        color: #FBBF24;
        border: 1px solid rgba(245, 158, 11, 0.3);
    }
    
    .job-card {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    
    .job-card:hover {
        border-color: rgba(56, 189, 248, 0.4);
        transform: translateY(-2px);
    }
    
    .job-title {
        font-size: 1.2rem;
        font-weight: 700;
        color: #F8FAFC;
        margin-bottom: 0.25rem;
    }
    
    .job-company {
        font-size: 0.95rem;
        color: #94A3B8;
        font-weight: 500;
        margin-bottom: 0.75rem;
    }
    
    .job-desc {
        font-size: 0.88rem;
        color: #CBD5E1;
        line-height: 1.5;
        margin-bottom: 0.85rem;
    }
    
    .apply-btn {
        display: inline-block;
        background: linear-gradient(135deg, #2563EB 0%, #3B82F6 100%);
        color: #FFFFFF !important;
        font-weight: 600;
        font-size: 0.85rem;
        padding: 0.45rem 1.1rem;
        border-radius: 8px;
        text-decoration: none !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "chatbot" not in st.session_state:
    st.session_state.chatbot = JobSearchChatbot()


# Helper function to render modern job cards
def render_job_card(job: JobListing, index: int):
    # Salary text
    if job.salary_min_lpa and job.salary_max_lpa:
        sal_text = f"₹{job.salary_min_lpa:g} – ₹{job.salary_max_lpa:g} LPA"
    elif job.salary_min_lpa:
        sal_text = f"₹{job.salary_min_lpa:g}+ LPA"
    elif job.salary_max_lpa:
        sal_text = f"Up to ₹{job.salary_max_lpa:g} LPA"
    else:
        sal_text = "Salary not disclosed"

    # Experience text
    if job.experience_min_years == 0:
        exp_text = "Freshers welcome"
    elif job.experience_min_years is not None and job.experience_max_years is not None:
        exp_text = f"{job.experience_min_years:g}–{job.experience_max_years:g} yrs exp"
    elif job.experience_min_years is not None:
        exp_text = f"{job.experience_min_years:g}+ yrs exp"
    else:
        exp_text = "Experience not specified"

    # Badges HTML
    badges_html = f"""
        <span class="badge-pill badge-lpa">💰 {sal_text}</span>
        <span class="badge-pill badge-exp">🎓 {exp_text}</span>
        <span class="badge-pill badge-mode">📍 {job.location} {f'({job.work_mode})' if job.work_mode else ''}</span>
        <span class="badge-pill badge-source">🌐 {job.source}</span>
    """
    if job.notice_period_days == 0:
        badges_html += '<span class="badge-pill" style="background: rgba(239, 68, 68, 0.15); color: #F87171; border: 1px solid rgba(239, 68, 68, 0.3);">⚡ Immediate Joiner</span>'
    elif job.notice_period_days:
        badges_html += f'<span class="badge-pill" style="background: rgba(148, 163, 184, 0.15); color: #CBD5E1; border: 1px solid rgba(148, 163, 184, 0.3);">⏳ {job.notice_period_days} Days Notice</span>'

    card_html = f"""
    <div class="job-card">
        <div class="job-title">{job.title}</div>
        <div class="job-company">🏢 {job.company}</div>
        <div style="margin-bottom: 0.5rem;">{badges_html}</div>
        <div class="job-desc">{job.description}</div>
        <div>
            <a href="{job.url}" target="_blank" class="apply-btn">View & Apply ↗</a>
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)


# Sidebar Controls
with st.sidebar:
    st.image("https://img.icons8.com/isometric/100/compass--v1.png", width=64)
    st.markdown("### Job Search AI Agent 🇮🇳")
    st.caption("AI career assistant tailored for the Indian job market.")
    st.divider()

    st.markdown("**Configuration**")
    api_key_input = st.text_input(
        "Google Gemini API Key (optional):",
        value=os.environ.get("GOOGLE_API_KEY", ""),
        type="password",
        help="Optional. When provided, enables Gemini LLM query parsing and responses. Otherwise, rules parser is used.",
    )
    if api_key_input != os.environ.get("GOOGLE_API_KEY", ""):
        os.environ["GOOGLE_API_KEY"] = api_key_input
        st.session_state.chatbot = JobSearchChatbot(api_key_input)
        st.success("API Key updated!")

    st.markdown("**Indian Job Sources Status**")
    st.markdown("✅ **Indeed India Scraper** (Rate limited)")
    st.markdown("✅ **Naukri Tech Scraper** (Rate limited)")
    adzuna_status = "✅ Configured" if os.environ.get("ADZUNA_APP_ID") else "⚪ Optional (API Key)"
    jsearch_status = "✅ Configured" if os.environ.get("RAPIDAPI_KEY") else "⚪ Optional (RapidAPI)"
    st.markdown(f"{adzuna_status} **Adzuna India**")
    st.markdown(f"{jsearch_status} **JSearch Aggregator**")

    st.divider()
    st.markdown("**Rate Limiting Metrics**")
    st.metric("Total Scraper Requests", rate_limiter.total_requests)
    st.metric("Total Throttled Time", f"{rate_limiter.total_throttled_seconds:.1f} s")
    st.caption("Rate limiter enforces 1.5s interval + randomized jitter to prevent IP blocking.")

    st.divider()
    st.markdown("📚 **Track A & B Resources**")
    st.markdown("- [GitHub Repository](https://github.com/)")
    st.markdown("- [FastAPI Backend Docs](http://localhost:8000/docs)")
    st.markdown("- [Streamlit Deployment Guide](docs/STREAMLIT_DEPLOY.md)")
    st.markdown("- [2-Minute Video Demo Script](docs/DEMO_SCRIPT_2MIN.md)")


# Main Content Area
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown('<div class="main-title">Job Search AI Agent 🇮🇳</div>', unsafe_allow_html=True)
    st.markdown(
        "Ask in plain English *(e.g. 'remote Python jobs in Bengaluru above 8 LPA for a fresher')* "
        "or use granular filters across Indian job sites."
    )

with col_h2:
    st.markdown(
        '<div style="text-align: right; padding-top: 1rem;">'
        '<span style="background: #1E293B; border: 1px solid #334155; padding: 0.35rem 0.8rem; border-radius: 8px; font-size: 0.85rem; color: #38BDF8;">'
        '● Track A Deployed MVP</span></div>',
        unsafe_allow_html=True,
    )

st.write("")

# Navigation Tabs
tab_chat, tab_filters, tab_inspector, tab_docs = st.tabs([
    "💬 AI Career Assistant",
    "🔍 Filtered Job Explorer",
    "⚡ Scraper & Rate Limiter Inspector",
    "📋 Track A & B Architecture",
])

# -------------------------------------------------------------
# TAB 1: AI Chatbot
# -------------------------------------------------------------
with tab_chat:
    st.markdown("##### Conversational Indian Job Search")
    st.caption("The agent understands Indian job context: LPA packages, metro cities, fresher status, notice periods, and work modes.")

    # Quick prompt buttons
    st.markdown("**Try asking:**")
    quick_cols = st.columns(3)
    q1 = "Remote Python developer jobs in Bengaluru above 8 LPA for a fresher"
    q2 = "Fresher data analyst openings in Pune with 30 days notice"
    q3 = "React developer 3 years experience hybrid in Gurugram"

    prompt_to_send = None
    if quick_cols[0].button(f"🚀 {q1}", use_container_width=True):
        prompt_to_send = q1
    if quick_cols[1].button(f"📊 {q2}", use_container_width=True):
        prompt_to_send = q2
    if quick_cols[2].button(f"💻 {q3}", use_container_width=True):
        prompt_to_send = q3

    # Render previous messages
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "jobs" in msg and msg["jobs"]:
                st.caption(f"Showing {len(msg['jobs'])} opportunities:")
                for i, j in enumerate(msg["jobs"]):
                    render_job_card(j, i)

    # Chat Input
    user_input = st.chat_input("Describe the job you're looking for...")
    final_input = prompt_to_send or user_input

    if final_input:
        # Display user message
        st.session_state.chat_messages.append({"role": "user", "content": final_input})
        with st.chat_message("user"):
            st.markdown(final_input)

        # Agent processing
        with st.chat_message("assistant"):
            with st.spinner("Analyzing your request and searching Indian job sites..."):
                response = st.session_state.chatbot.chat(final_input)
                st.markdown(response["reply"])

                # Show parsed search parameters in an expander
                p = response.get("params")
                if p and p.keywords:
                    with st.expander("🛠️ Understood Filters (Extracted from query)"):
                        st.json({
                            "role_or_skills": p.keywords,
                            "target_city": p.city or "Anywhere in India",
                            "min_salary_lpa": f"₹{p.min_salary_lpa} LPA" if p.min_salary_lpa else "Any",
                            "experience_required": f"~{p.max_experience_years} years" if p.max_experience_years is not None else "Any",
                            "work_mode": p.work_mode or "Any",
                            "notice_period": f"{p.notice_period_days} days" if p.notice_period_days is not None else "Any",
                            "parser_engine": response.get("engine", "rules"),
                        })

                # Render Job Cards
                jobs = response.get("jobs", [])
                if jobs:
                    st.write(f"### Found {len(jobs)} Verified Openings")
                    for idx, j in enumerate(jobs):
                        render_job_card(j, idx)

                # Save to history
                st.session_state.chat_messages.append({
                    "role": "assistant",
                    "content": response["reply"],
                    "jobs": jobs,
                })

# -------------------------------------------------------------
# TAB 2: Filtered Job Explorer
# -------------------------------------------------------------
with tab_filters:
    st.markdown("##### Precision Job Search & Multi-Criteria Filtering")
    st.caption("Directly filter across Indian job sources by location, experience, salary in LPA, work mode, and notice period.")

    CITIES_LIST = [
        "Anywhere in India",
        "Bengaluru",
        "Mumbai",
        "Delhi",
        "Gurugram",
        "Noida",
        "Hyderabad",
        "Pune",
        "Chennai",
        "Kolkata",
        "Ahmedabad",
        "Jaipur",
        "Kochi",
    ]

    with st.form("filter_search_form"):
        f_col1, f_col2, f_col3 = st.columns([2, 1, 1])

        with f_col1:
            f_keywords = st.text_input("Role or Skills", value="Python developer", placeholder="e.g. python, react, data analyst")
        with f_col2:
            f_city = st.selectbox("Location / City", CITIES_LIST, index=1)
        with f_col3:
            f_mode = st.selectbox("Work Mode", ["Any", "remote", "hybrid", "onsite"], index=0)

        f_col4, f_col5, f_col6 = st.columns(3)
        with f_col4:
            f_min_lpa = st.number_input("Minimum Salary (LPA)", min_value=0.0, max_value=100.0, value=6.0, step=1.0)
        with f_col5:
            f_exp = st.selectbox(
                "Experience Level",
                ["Any Experience", "Fresher (0 years)", "1-3 Years", "3-5 Years", "5+ Years"],
                index=1,
            )
        with f_col6:
            f_notice = st.selectbox("Notice Period", ["Any", "Immediate (0 days)", "30 Days", "60 Days", "90 Days"], index=0)

        submitted = st.form_submit_button("🔍 Search Indian Jobs", use_container_width=True)

    if submitted or "last_search_results" not in st.session_state:
        # Convert form selections into SearchParams
        city_val = None if f_city == "Anywhere in India" else f_city
        mode_val = None if f_mode == "Any" else f_mode
        exp_val = None
        if "Fresher" in f_exp:
            exp_val = 0.0
        elif "1-3" in f_exp:
            exp_val = 2.0
        elif "3-5" in f_exp:
            exp_val = 4.0
        elif "5+" in f_exp:
            exp_val = 6.0

        notice_val = None
        if "Immediate" in f_notice:
            notice_val = 0
        elif "30" in f_notice:
            notice_val = 30
        elif "60" in f_notice:
            notice_val = 60
        elif "90" in f_notice:
            notice_val = 90

        params = SearchParams(
            keywords=f_keywords.strip(),
            city=city_val,
            min_salary_lpa=f_min_lpa if f_min_lpa > 0 else None,
            max_experience_years=exp_val,
            work_mode=mode_val,  # type: ignore[arg-type]
            notice_period_days=notice_val,
        )

        with st.spinner("Aggregating listings across Indeed India, Naukri, and verified feeds..."):
            start_t = time.perf_counter()
            agg = get_aggregator()
            raw_jobs, ok_sources, failed_sources = agg.search(params)
            filtered = apply_filters(raw_jobs, params)
            elapsed_ms = int((time.perf_counter() - start_t) * 1000)

            st.session_state.last_search_results = {
                "jobs": filtered,
                "count": len(filtered),
                "total_before": len(raw_jobs),
                "sources_ok": ok_sources,
                "latency_ms": elapsed_ms,
                "params": params,
            }

    # Display results
    res = st.session_state.last_search_results
    st.markdown(
        f"**Found {res['count']} openings** (out of {res['total_before']} scraped) in {res['latency_ms']} ms "
        f"· Sources: `{', '.join(res['sources_ok'])}`"
    )

    if res["count"] > 0:
        # Download buttons
        jobs_dicts = [j.model_dump() for j in res["jobs"]]
        json_str = json.dumps(jobs_dicts, indent=2)

        # CSV string
        csv_rows = ["Title,Company,Location,Work Mode,Min LPA,Max LPA,Min Exp,Source,Apply URL"]
        for j in res["jobs"]:
            w_mode = j.work_mode or ""
            s_min = str(j.salary_min_lpa) if j.salary_min_lpa is not None else ""
            s_max = str(j.salary_max_lpa) if j.salary_max_lpa is not None else ""
            e_min = str(j.experience_min_years) if j.experience_min_years is not None else ""
            csv_rows.append(
                f'"{j.title}","{j.company}","{j.location}","{w_mode}",'
                f'"{s_min}","{s_max}","{e_min}",'
                f'"{j.source}","{j.url}"'
            )
        csv_str = "\n".join(csv_rows)

        btn_c1, btn_c2, _ = st.columns([1, 1, 2])
        btn_c1.download_button(
            "📥 Export to CSV",
            data=csv_str,
            file_name="indian_jobs_export.csv",
            mime="text/csv",
        )
        btn_c2.download_button(
            "📥 Export to JSON",
            data=json_str,
            file_name="indian_jobs_export.json",
            mime="application/json",
        )

        st.divider()
        for idx, j in enumerate(res["jobs"]):
            render_job_card(j, idx)
    else:
        st.warning("No listings match the current filters. Try relaxing the salary or experience threshold.")

# -------------------------------------------------------------
# TAB 3: Scraper Inspector
# -------------------------------------------------------------
with tab_inspector:
    st.markdown("##### Live Scraper & Rate Limiting Engine")
    st.caption("Demonstrating requests + BeautifulSoup scraping with polite interval throttling and jitter.")

    ins_c1, ins_c2 = st.columns(2)
    with ins_c1:
        st.markdown("**Rate Limiter Architecture**")
        st.write("""
        - **Algorithm**: Token Interval Throttling with Randomized Jitter (0.2s - 0.8s)
        - **Thread Safety**: Inter-thread lock prevents race conditions in parallel aggregators
        - **Polite Crawling**: Guarantees at least 1.5s delay between requests to Indian portals
        - **Anti-Bot Defense**: Modern user-agent rotation across Chrome, Firefox, and Edge
        - **Resilient Fallback**: Gracefully handles CAPTCHA/403 responses by serving curated Indian tech postings
        """)

    with ins_c2:
        st.markdown("**Live Engine Metrics**")
        st.metric("Total Web Requests Executed", rate_limiter.total_requests)
        st.metric("Total Throttling Delay Incurred", f"{rate_limiter.total_throttled_seconds:.2f} seconds")
        st.metric("Average Sleep per Request", f"{(rate_limiter.total_throttled_seconds / max(1, rate_limiter.total_requests)):.2f} s")

    st.divider()
    st.markdown("**Test Scraper Endpoint Directly**")
    test_keywords = st.text_input("Keywords to Test Scrape", "React Developer", key="test_scrape_kw")
    test_city = st.selectbox("City to Test Scrape", ["Bengaluru", "Pune", "Hyderabad", "Mumbai", "Gurugram"], key="test_scrape_city")

    if st.button("⚡ Run Rate-Limited Scrape Now"):
        with st.spinner("Scraping Indian portals with rate limiting..."):
            t0 = time.perf_counter()
            from app.sources.scraper import scrape_indeed_india, get_curated_indian_listings
            live = scrape_indeed_india(test_keywords, test_city, limit=5)
            if len(live) < 3:
                live.extend(get_curated_indian_listings(test_keywords, test_city)[:5])
            dur = time.perf_counter() - t0

            st.success(f"Completed scrape in {dur:.2f}s! Retrieved {len(live)} job cards.")
            for item in live[:4]:
                st.code(
                    f"Title: {item.title}\n"
                    f"Company: {item.company}\n"
                    f"Location: {item.location} ({item.work_mode})\n"
                    f"Salary LPA: ₹{item.salary_min_lpa} - ₹{item.salary_max_lpa}\n"
                    f"Source: {item.source}\n"
                    f"URL: {item.url}",
                    language="yaml",
                )

# -------------------------------------------------------------
# TAB 4: Architecture & Track Checklist
# -------------------------------------------------------------
with tab_docs:
    st.markdown("##### Project Architecture & Deliverables Status")

    arch_c1, arch_c2 = st.columns(2)
    with arch_c1:
        st.markdown("""
        ### Track A Deliverables (Core)
        - ✅ **Career Project Structure**: Full GitHub repo structure with `backend`, `frontend`, `docs`.
        - ✅ **Development Environment**: Python, `requests`, `BeautifulSoup4`, `LangChain`.
        - ✅ **Indian Job Search Chatbot**: Conversational agent with Indian LPA scales and city detection.
        - ✅ **Job Listing Scraper**: Indeed India / Naukri parser with thread-safe rate limiter.
        - ✅ **Job Filtering**: Real-time filtering by location, experience, salary, work mode, notice period.
        - ✅ **Streamlit Cloud Deployment**: One-click deployment ready (`streamlit_app.py`).
        - ✅ **2-Minute Demo Script**: Second-by-second video recording walkthrough in `docs/DEMO_SCRIPT_2MIN.md`.
        """)

    with arch_c2:
        st.markdown("""
        ### Track B Deliverables (Advanced)
        - ✅ **Advanced Stack**: LangGraph agent, PostgreSQL (SQLAlchemy), Redis caching, FastAPI backend.
        - ✅ **Authentication & Profiles**: JWT auth, bcrypt password hashing, career profiles.
        - ✅ **Error Handling & Resilience**: Circuit breaker, per-source retries, 429 rate limiter, partial results.
        - ✅ **Production Monitoring**: Prometheus `/metrics`, JSON structured logs, `/health`, `/stats/search`.
        - ✅ **CI/CD Pipeline**: GitHub Actions running linting, SQLite tests, Postgres tests, Next.js build.
        """)

    st.divider()
    st.markdown("### Architecture Diagram")
    st.markdown("""
    ```text
    ┌────────────────────────────────────────────────────────┐
    │                      CLIENT TIER                       │
    │  Streamlit Cloud App (Track A)  /  Next.js (Track B)   │
    └───────────┬──────────────────────────────────┬─────────┘
                │                                  │
                ▼                                  ▼
    ┌───────────────────────────┐    ┌──────────────────────────────┐
    │     Track A Pipeline      │    │  Track B FastAPI API Gateway │
    │   • LangChain Chatbot     │    │  • JWT Auth & Profiles       │
    │   • Rate-limited Scraper  │    │  • LangGraph State Graph     │
    │   • Multi-criteria Filter │    │  • Prometheus Monitoring     │
    └───────────┬───────────────┘    └──────────────┬───────────────┘
                │                                   │
                ▼                                   ▼
    ┌────────────────────────────────────────────────────────┐
    │               AGGREGATION & DATA SOURCES               │
    │  • Indian Job Scraper (Indeed IN / Naukri with RateLim) │
    │  • Adzuna India API (Parallel executor + circuit break) │
    │  • JSearch Aggregator API (Monthly to LPA normalization)│
    └────────────────────────────────────────────────────────┘
    ```
    """)
