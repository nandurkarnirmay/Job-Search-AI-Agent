"""Week 2 job-search agent as a LangGraph workflow:

    parse_query --(ok)--> search --> respond --> END
          \\--(error)------------------^

Weeks 3-4 add more tool nodes (company research, resume analysis, interview prep, salary research)
behind a router node; the state and the parse/search/respond nodes stay as they are."""
import logging
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agent.llm import get_llm
from app.domain import JobListing, SearchOutcome, SearchParams
from app.errors import AllSourcesFailedError
from app.monitoring import LLM_CALLS
from app.services.query_parser import parse_query
from app.services.search_service import run_search

log = logging.getLogger("app.agent")

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


class AgentState(TypedDict, total=False):
    message: str
    profile_defaults: dict
    params: SearchParams
    parser: Literal["llm", "rules"]
    outcome: SearchOutcome
    error: str
    reply: str


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
    return {"params": params, "parser": parser}


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


def respond_node(state: AgentState) -> AgentState:
    if state.get("error"):
        return {"reply": state["error"]}
    outcome, p = state["outcome"], state["params"]
    if not outcome.jobs:
        hint = " Try removing the salary or experience filter." if (p.min_salary_lpa or p.max_experience_years) \
            else " Try a broader role or another city."
        return {"reply": f"I couldn't find openings for {_describe(p)}.{hint}"}
    top = outcome.jobs[:5]
    lines = [f"Found {len(outcome.jobs)} openings for {_describe(p)}. Top matches:"]
    lines += [f"{i}. {j.title} at {j.company}, {j.location} ({_salary(j)})" for i, j in enumerate(top, 1)]
    if outcome.sources_failed:
        lines.append(f"Note: {', '.join(outcome.sources_failed)} didn't respond, so results may be incomplete.")
    return {"reply": "\n".join(lines)}


def _after_parse(state: AgentState) -> str:
    return "respond" if state.get("error") else "search"


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("parse_query", parse_node)
    g.add_node("search", search_node)
    g.add_node("respond", respond_node)
    g.add_edge(START, "parse_query")
    g.add_conditional_edges("parse_query", _after_parse, {"search": "search", "respond": "respond"})
    g.add_edge("search", "respond")
    g.add_edge("respond", END)
    return g.compile()


_graph = None


def run_agent(message: str, profile_defaults: dict | None = None) -> AgentState:
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph.invoke({"message": message, "profile_defaults": profile_defaults or {}})
