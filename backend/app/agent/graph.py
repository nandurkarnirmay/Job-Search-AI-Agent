"""Career agent as a LangGraph workflow (Week 4: 6 tools).

                    ┌─ job_search ──────► parse_query ──► search ──► respond_jobs ─┐
                    ├─ refine_search ──────────────────► search                    │
                    ├─ company_research ──► company ───────────────────────────────┤
    START ─► route ─┼─ salary_research ───► salary ────────────────────────────────┤─► END
                    ├─ resume_review / resume_match ──► resume ────────────────────┤
                    ├─ interview_prep ────► interview ─────────────────────────────┤
                    ├─ track_application / applications_status ──► tracker ────────┤
                    └─ help ──────────────► help ──────────────────────────────────┘

`route` uses rules first and asks the LLM only when no rule matches. Conversation memory (previous search,
previous results, recent messages) comes in through the state, so follow-ups like "what about Pune?",
"tell me about the second company" or "how does my resume match the first job?" work. Tools that need the
user's data (resume, tracker, interview sessions) get a ToolContext with the DB session and user."""
import logging
from dataclasses import dataclass
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.agent.llm import get_llm
from app.agent.router import Intent, Route, merge_refinement, role_and_company, route
from app.domain import CompanyReport, JobListing, SalaryReport, SearchOutcome, SearchParams
from app.errors import AllSourcesFailedError, ConflictError
from app.monitoring import AGENT_INTENTS, LLM_CALLS
from app.schemas import ApplicationOut
from app.services.applications import add_application, pipeline
from app.services.company_research import company_reply, overview, research_company
from app.services.interview import create_session, interview_out
from app.services.query_parser import parse_query
from app.services.resume_analysis import ats_match, ats_reply, review_for_role, review_reply
from app.services.resume_parser import from_row
from app.services.salary_research import research_salary, salary_reply
from app.services.search_service import get_job, run_search

log = logging.getLogger("app.agent")

HELP_TEXT = ("I'm your job search assistant for India. I can:\n"
             "• Find jobs: tell me what role you're looking for, e.g. 'data analyst jobs in Pune above 6 LPA'\n"
             "• Refine a search: 'what about Bengaluru?', 'only remote', 'show more'\n"
             "• Research a company: 'tell me about Infosys' or 'tell me about the second company'\n"
             "• Check salaries: 'average salary of a React developer in Hyderabad with 3 years'\n"
             "• Check your resume: 'review my resume for data analyst roles',\n"
             "  'how does my resume match the first job?'\n"
             "• Practise interviews: 'interview questions for a Java developer', 'prepare me for the second job'\n"
             "• Track applications: 'save the first job', 'show my applications'")

ROUTE_PROMPT = """Classify the latest message sent to a career assistant for the Indian job market.
Intents:
- job_search: wants job openings for a role
- refine_search: changes the previous search ({last_search}) without naming a new role
- company_research: wants to know about one specific employer; set company to its name exactly as written
- salary_research: wants pay information for a role
- resume_review: wants feedback on their resume or their skill gaps
- interview_prep: wants interview questions or practice for a role
- applications_status: asks about the jobs they saved or applied to
- help: greeting, unclear, or outside job search
Recent conversation:
{history}
Latest message: {message}"""

PARSE_PROMPT = """You convert a job seeker's message into search filters for the Indian job market.
Rules:
- keywords: the role and key skills only (e.g. "python backend developer"). No city, salary or filler words.
- city: one Indian city if mentioned, in its official modern name (Bengaluru, Gurugram, Mumbai).
- min_salary_lpa: minimum salary in lakhs per annum, only if stated. "8L", "8 lakhs", "8 LPA" -> 8.
- max_experience_years: the user's experience; freshers/graduates -> 0. Only if stated or implied.
- work_mode: remote / hybrid / onsite, only if stated.
- notice_period_days: the user's notice period, only if stated.
- Leave a field null when the message does not say it. Never guess.
Defaults from the user's saved profile (use only when the message is silent on that field): {profile}

Message: {message}"""




class RouteDecision(BaseModel):
    intent: Intent
    company: str | None = Field(default=None, description="Employer name exactly as written in the message")


class AgentState(TypedDict, total=False):
    # inputs
    message: str
    profile_defaults: dict
    last_params: SearchParams | None
    last_jobs: list[dict]
    history: list[dict]
    # working state
    intent: Intent
    router: Literal["llm", "rules"]
    llm_used: bool
    company_name: str
    help_note: str
    params: SearchParams
    parser: Literal["llm", "rules"]
    role: str
    job_ref: dict
    tools: "ToolContext"
    # outputs
    outcome: SearchOutcome
    company: CompanyReport
    salary: SalaryReport
    error: str
    reply: str
    extras: dict[str, Any]  # Week 4 cards: ats, resume_review, interview, application, pipeline


@dataclass
class ToolContext:
    """What user-data tools need. Absent (None) in contexts without a logged-in user."""

    db: Any   # sqlalchemy Session
    user: Any  # models.User


def _llm_route(decision: RouteDecision, state: AgentState) -> Route | None:
    """Accept the LLM's intent only if it is consistent with the message (no invented companies/roles)."""
    message, last = state["message"], state.get("last_params")
    parsed = parse_query(message)
    if decision.intent == "company_research":
        name = (decision.company or "").strip()
        return Route("company_research", company=name) if name and name.lower() in message.lower() else None
    if decision.intent == "salary_research":
        return Route("salary_research", params=parsed) if parsed.keywords else None
    if decision.intent == "refine_search":
        return Route("refine_search", params=merge_refinement(last, message, parsed)) if last else None
    if decision.intent in ("resume_review", "interview_prep"):
        role, company = role_and_company(message)
        role = role or state.get("profile_defaults", {}).get("keywords") or (last.keywords if last else None)
        if decision.intent == "interview_prep" and not role:
            return None
        return Route(decision.intent, role=role, company=company)
    if decision.intent == "applications_status":
        return Route("applications_status")
    if decision.intent in ("resume_match", "track_application"):
        return None  # these need an explicit earlier result ("the second job"): rules handle them
    if decision.intent == "job_search":
        has_role = parsed.keywords or state.get("profile_defaults", {}).get("keywords")
        return Route("job_search", params=parsed) if has_role else None
    return Route("help")


def route_node(state: AgentState) -> AgentState:
    defaults = state.get("profile_defaults", {})
    r = route(state["message"], last_params=state.get("last_params"), last_jobs=state.get("last_jobs") or [],
              default_keywords=defaults.get("keywords"))
    router: Literal["llm", "rules"] = "rules"
    llm = get_llm()
    if not r.confident and llm is not None:
        history = "\n".join(f"{m['role']}: {m['content'][:200]}" for m in (state.get("history") or [])[-4:])
        last = state.get("last_params")
        try:
            decision = llm.with_structured_output(RouteDecision).invoke(ROUTE_PROMPT.format(
                last_search=last.keywords if last else "none", history=history or "none",
                message=state["message"]))
            LLM_CALLS.labels("route", "ok").inc()
            if accepted := _llm_route(decision, state):
                r, router = accepted, "llm"
            else:
                LLM_CALLS.labels("route", "rejected").inc()
        except Exception as e:
            LLM_CALLS.labels("route", "error").inc()
            log.warning("LLM routing failed, using rules: %s", e)
    AGENT_INTENTS.labels(r.intent, router).inc()
    out: AgentState = {"intent": r.intent, "router": router, "llm_used": router == "llm", "parser": "rules"}
    if r.company:
        out["company_name"] = r.company
    if r.params is not None:
        out["params"] = r.params
    if r.notes:
        out["help_note"] = r.notes[0]
    if r.role:
        out["role"] = r.role
    if r.job_ref:
        out["job_ref"] = r.job_ref
    return out


def parse_node(state: AgentState) -> AgentState:
    message, defaults = state["message"], state.get("profile_defaults", {})
    rules = parse_query(message)
    llm = get_llm()
    params, parser = rules, "rules"
    if llm is not None:
        try:
            structured = llm.with_structured_output(SearchParams)
            params = structured.invoke(PARSE_PROMPT.format(profile=defaults or "none", message=message))
            parser = "llm"
            LLM_CALLS.labels("parse", "ok").inc()
            # Guard against hallucinated numbers: keep a number only if the rules parser also found it
            # in the text or it came from the profile defaults.
            for field in ("min_salary_lpa", "max_experience_years", "notice_period_days"):
                llm_val = getattr(params, field)
                if llm_val is not None and getattr(rules, field) is None and defaults.get(field) != llm_val:
                    setattr(params, field, None)
        except Exception as e:
            LLM_CALLS.labels("parse", "error").inc()
            log.warning("LLM parse failed, falling back to rules: %s", e)
            params, parser = rules, "rules"

    # Fill gaps from the saved profile (message always wins).
    for field, value in defaults.items():
        if getattr(params, field, None) in (None, "") and value not in (None, ""):
            setattr(params, field, value)
    if not params.keywords:
        return {"params": params, "parser": parser,
                "error": "Tell me what role you're looking for, e.g. 'data analyst jobs in Pune above 6 LPA'."}
    return {"params": params, "parser": parser, "llm_used": state.get("llm_used") or parser == "llm"}



def search_node(state: AgentState) -> AgentState:
    try:
        return {"outcome": run_search(state["params"])}
    except AllSourcesFailedError as e:
        return {"error": e.message}


def _describe(p: SearchParams) -> str:
    bits = [p.keywords]
    if p.city:
        bits.append(f"in {p.city}")
    if p.work_mode:
        bits.append(f"({p.work_mode})")
    if p.min_salary_lpa is not None:
        bits.append(f"paying {p.min_salary_lpa:g}+ LPA")
    if p.max_experience_years is not None:
        bits.append("for freshers" if p.max_experience_years == 0 else f"for ~{p.max_experience_years:g} yrs exp")
    return " ".join(bits)


def _salary(j: JobListing) -> str:
    if j.salary_min_lpa is None and j.salary_max_lpa is None:
        return "salary not disclosed"
    lo, hi = j.salary_min_lpa or j.salary_max_lpa, j.salary_max_lpa or j.salary_min_lpa
    return f"₹{lo:g} LPA" if lo == hi else f"₹{lo:g}–{hi:g} LPA"


def respond_jobs_node(state: AgentState) -> AgentState:
    if state.get("error"):
        return {"reply": state["error"]}
    outcome, p = state["outcome"], state["params"]
    if not outcome.jobs:
        hint = " Try removing the salary or experience filter." if (p.min_salary_lpa or p.max_experience_years) \
            else " Try a broader role or another city."
        return {"reply": f"I couldn't find openings for {_describe(p)}.{hint}"}
    top = outcome.jobs[:5]
    n = len(outcome.jobs)
    lines = [f"Found {n} opening{'s' if n != 1 else ''} for {_describe(p)}. Top matches:"]
    lines += [f"{i}. {j.title} at {j.company}, {j.location} ({_salary(j)})" for i, j in enumerate(top, 1)]
    if outcome.sources_failed:
        lines.append(f"Note: {', '.join(outcome.sources_failed)} didn't respond, so results may be incomplete.")
    return {"reply": "\n".join(lines)}



def company_node(state: AgentState) -> AgentState:
    report = research_company(state["company_name"])
    text, how = overview(report)
    return {"company": report, "reply": company_reply(report, text),
            "llm_used": state.get("llm_used") or how == "llm"}


def salary_node(state: AgentState) -> AgentState:
    report = research_salary(state["params"])
    return {"salary": report, "reply": salary_reply(report)}


NEEDS_LOGIN = "Log in to use your resume, interview practice and application tracker."


def resume_node(state: AgentState) -> AgentState:
    ctx = state.get("tools")
    if ctx is None:
        return {"reply": NEEDS_LOGIN}
    if ctx.user.resume is None:
        return {"reply": "Upload your resume on the Resume page first (PDF or DOCX), then ask me again."}
    resume = from_row(ctx.user.resume)
    if state["intent"] == "resume_match":
        ref = state["job_ref"]
        job = get_job(ref["id"])
        m = ats_match(resume, ref["title"], job.description if job else "", ref.get("company"))
        if job is None:
            m.notes.append("That job's description is no longer cached, so only the title was compared. "
                           "Search again for a full match.")
        return {"reply": ats_reply(m), "extras": {"ats": m.model_dump()}}
    rev = review_for_role(resume, state.get("role"))
    return {"reply": review_reply(rev), "extras": {"resume_review": rev.model_dump()}}


def interview_node(state: AgentState) -> AgentState:
    ctx = state.get("tools")
    if ctx is None:
        return {"reply": NEEDS_LOGIN}
    role, company, description = state["role"], state.get("company_name"), ""
    if ref := state.get("job_ref"):
        company = ref.get("company")
        if job := get_job(ref["id"]):
            description = job.description
    session, notes = create_session(ctx.db, ctx.user, role, company, description)
    out = interview_out(session, notes)
    at = f" at {company}" if company else ""
    lines = [f"Practice set for {role}{at}: {len(out.questions)} questions. Answer them on the practice page "
             "for feedback on each one. First three:"]
    lines += [f"{i}. {q.text}" for i, q in enumerate(out.questions[:3], 1)]
    lines += notes
    return {"reply": "\n".join(lines), "extras": {"interview": out.model_dump(mode="json")}}


def tracker_node(state: AgentState) -> AgentState:
    ctx = state.get("tools")
    if ctx is None:
        return {"reply": NEEDS_LOGIN}
    if state["intent"] == "track_application":
        ref = state["job_ref"]
        try:
            app = add_application(ctx.db, ctx.user.id, job_id=ref["id"], title=ref["title"], company=ref["company"],
                                  location=ref.get("location", ""), url=ref.get("url"))
        except ConflictError as e:
            return {"reply": f"{ref['title']} at {ref['company']}: {e.message}"}
        out = ApplicationOut.model_validate(app, from_attributes=True)
        return {"reply": f"Saved {app.title} at {app.company} to your tracker (status: saved). Move it to "
                         "'applied' on the Tracker page once you apply.",
                "extras": {"application": out.model_dump(mode="json")}}
    counts = pipeline(ctx.db, ctx.user.id)
    total = sum(counts.values())
    if not total:
        return {"reply": "Your tracker is empty. Save jobs from search results ('save the first job').",
                "extras": {"pipeline": counts}}
    active = ", ".join(f"{n} {s}" for s, n in counts.items() if n)
    return {"reply": f"You're tracking {total} job{'s' if total != 1 else ''}: {active}.",
            "extras": {"pipeline": counts}}


def help_node(state: AgentState) -> AgentState:
    note = state.get("help_note")
    return {"reply": f"{note}\n\n{HELP_TEXT}" if note else HELP_TEXT}


def _after_route(state: AgentState) -> str:
    return {"job_search": "parse_query", "refine_search": "search", "company_research": "company",
            "salary_research": "salary", "resume_review": "resume", "resume_match": "resume",
            "interview_prep": "interview", "track_application": "tracker", "applications_status": "tracker",
            "help": "help"}[state["intent"]]


def _after_parse(state: AgentState) -> str:
    return "respond_jobs" if state.get("error") else "search"


def build_graph():
    g = StateGraph(AgentState)
    for name, fn in [("route", route_node), ("parse_query", parse_node), ("search", search_node),
                     ("respond_jobs", respond_jobs_node), ("company", company_node), ("salary", salary_node),
                     ("resume", resume_node), ("interview", interview_node), ("tracker", tracker_node),
                     ("help", help_node)]:
        g.add_node(name, fn)
    g.add_edge(START, "route")
    g.add_conditional_edges("route", _after_route, ["parse_query", "search", "company", "salary", "resume",
                                                    "interview", "tracker", "help"])
    g.add_conditional_edges("parse_query", _after_parse, ["search", "respond_jobs"])
    g.add_edge("search", "respond_jobs")
    for terminal in ("respond_jobs", "company", "salary", "resume", "interview", "tracker", "help"):
        g.add_edge(terminal, END)
    return g.compile()


_graph = None


def run_agent(message: str, profile_defaults: dict | None = None, context: dict | None = None,
              tools: ToolContext | None = None) -> AgentState:
    """context: {"last_params": SearchParams | None, "last_jobs": [compact jobs], "history": [messages]}"""
    global _graph
    if _graph is None:
        _graph = build_graph()
    ctx = context or {}
    return _graph.invoke({"message": message, "profile_defaults": profile_defaults or {},
                          "last_params": ctx.get("last_params"), "last_jobs": ctx.get("last_jobs") or [],
                          "history": ctx.get("history") or [], "tools": tools})
