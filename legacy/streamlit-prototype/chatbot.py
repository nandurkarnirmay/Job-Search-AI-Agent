"""Track A: Basic Job Search Chatbot with Indian Job Sites using LangChain.

Supports:
- Conversational multi-turn memory
- Natural language parsing for Indian job requirements (LPA, cities, experience, work mode)
- Multi-source search across Indian job portals
- Gemini LLM integration via LangChain with graceful rule-based fallback
"""
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
for p in (str(BACKEND), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from app.domain import JobListing, SearchParams
from app.services.filters import apply_filters
from app.services.query_parser import parse_query
from app.sources.aggregator import get_aggregator


class JobSearchChatbot:
    """Conversational AI Agent for Indian Job Search built with LangChain & fallback rules."""

    def __init__(self, google_api_key: str | None = None):
        self.api_key = google_api_key or os.environ.get("GOOGLE_API_KEY", "")
        self.history: list[dict[str, str]] = []
        self.last_params: SearchParams | None = None
        self._init_llm()

    def _init_llm(self):
        self.llm = None
        if self.api_key:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                self.llm = ChatGoogleGenerativeAI(
                    model="gemini-2.5-flash",
                    google_api_key=self.api_key,
                    temperature=0.2,
                )
            except Exception:
                # LLM initialization failed, will use rule-based parser
                self.llm = None

    def reset(self):
        """Clear conversation history."""
        self.history.clear()
        self.last_params = None

    def chat(self, user_message: str) -> dict[str, Any]:
        """Process user message, search Indian job listings, and return conversational reply + job cards."""
        # 1. Parse query to search parameters
        params = parse_query(user_message)

        # Merge with previous context if user is refining search (e.g. "now make it remote")
        if self.last_params and not params.keywords:
            if params.city or params.min_salary_lpa or params.work_mode or params.max_experience_years:
                params.keywords = self.last_params.keywords
                if not params.city:
                    params.city = self.last_params.city

        # If keywords still empty, guide the user
        if not params.keywords:
            reply = (
                "Namaste! 🙏 I'm your Indian Job Search Assistant. What kind of role are you looking for?\n\n"
                "Try asking something like:\n"
                "- *'Remote Python developer jobs in Bengaluru above 8 LPA for a fresher'*\n"
                "- *'React developer with 3 years experience hybrid in Gurugram'*\n"
                "- *'Data analyst openings in Pune with 30 days notice'*"
            )
            self.history.append({"role": "user", "content": user_message})
            self.history.append({"role": "assistant", "content": reply})
            return {
                "reply": reply,
                "params": params,
                "jobs": [],
                "engine": "rules",
            }

        self.last_params = params

        # 2. Run multi-source search
        aggregator = get_aggregator()
        raw_jobs, ok_sources, failed_sources = aggregator.search(params)
        filtered_jobs = apply_filters(raw_jobs, params)

        # 3. Generate conversational reply
        engine_used = "rules"
        if self.llm:
            try:
                from langchain_core.messages import HumanMessage, SystemMessage

                sys_prompt = (
                    "You are an encouraging Indian Career Advisor AI. Respond concisely in 2-3 sentences. "
                    "Acknowledge the role, location, and constraints found. Highlight top companies and salaries in LPA. "
                    "If no jobs matched, suggest loosening salary or experience filters."
                )
                user_prompt = (
                    f"User asked: '{user_message}'\n"
                    f"Parsed filters: Role='{params.keywords}', City='{params.city}', "
                    f"Min Salary='{params.min_salary_lpa} LPA', Exp='{params.max_experience_years} yrs', "
                    f"Work Mode='{params.work_mode}'.\n"
                    f"Found {len(filtered_jobs)} matching jobs out of {len(raw_jobs)} total.\n"
                    f"Top 3 job titles & companies: "
                    + ", ".join([f"{j.title} at {j.company} (₹{j.salary_min_lpa or 'N/A'}-{j.salary_max_lpa or 'N/A'} LPA)" for j in filtered_jobs[:3]])
                )
                response = self.llm.invoke([SystemMessage(content=sys_prompt), HumanMessage(content=user_prompt)])
                reply = str(response.content)
                engine_used = "langchain-gemini"
            except Exception:
                reply = self._build_rule_reply(params, filtered_jobs, ok_sources)
        else:
            reply = self._build_rule_reply(params, filtered_jobs, ok_sources)

        self.history.append({"role": "user", "content": user_message})
        self.history.append({"role": "assistant", "content": reply})

        return {
            "reply": reply,
            "params": params,
            "jobs": filtered_jobs,
            "engine": engine_used,
            "sources_ok": ok_sources,
            "sources_failed": failed_sources,
        }

    def _build_rule_reply(self, p: SearchParams, jobs: list[JobListing], sources: list[str]) -> str:
        parts = [f"role '{p.keywords}'"]
        if p.city:
            parts.append(f"in {p.city}")
        if p.work_mode:
            parts.append(f"({p.work_mode})")
        if p.min_salary_lpa:
            parts.append(f"above {p.min_salary_lpa:g} LPA")
        if p.max_experience_years is not None:
            parts.append("for freshers" if p.max_experience_years == 0 else f"for ~{p.max_experience_years:g} yrs exp")

        desc = " ".join(parts)
        if not jobs:
            return (
                f"I searched Indian job sources ({', '.join(sources)}) for {desc}, "
                f"but found no exact matches. Try loosening the salary threshold or searching for nearby cities."
            )

        top_preview = ", ".join([f"{j.company} ({j.title})" for j in jobs[:3]])
        return (
            f"🎯 Found **{len(jobs)} openings** for {desc} across Indian tech job portals.\n\n"
            f"Top hiring companies include: **{top_preview}**. Check out the listings below to apply!"
        )
