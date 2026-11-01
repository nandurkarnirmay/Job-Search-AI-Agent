"""Rule-based intent router. Pure functions so every routing decision is unit-testable.

Intents:
  job_search       "python jobs in pune above 8 lpa"
  refine_search    follow-up on the previous search: "what about Bengaluru?", "only remote", "show more"
  company_research "tell me about Infosys", "tell me about the second company"
  salary_research  "average salary of a data analyst in Pune"
  resume_review    "review my resume for data analyst roles", "what skills am I missing?"
  resume_match     "how well does my resume match the second job?"
  interview_prep   "interview questions for a python developer", "prepare me for the first job"
  track_application "save the second job"
  applications_status "show my applications"
  help             greetings, empty or unclear messages

Follow-ups can also remove filters: "any city", "remove the salary filter", "clear filters".

`confident=False` means no rule matched; the graph may then ask the LLM (saves free-tier quota and latency:
the LLM is only called for messages the rules cannot place)."""
import re
from dataclasses import dataclass, field
from typing import Literal

from app.domain import SearchParams
from app.services.query_parser import parse_query

Intent = Literal["job_search", "refine_search", "company_research", "salary_research", "resume_review",
                 "resume_match", "interview_prep", "track_application", "applications_status", "help"]

JOB_WORDS = re.compile(r"\b(jobs?|openings?|vacanc(?:y|ies)|roles?|positions?|hiring|opportunit(?:y|ies)|"
                       r"internships?|apply|listings?)\b", re.I)
SALARY_WORDS = re.compile(r"\b(salary|salaries|how much|earn|earns|earning|pay scale|paid|package|ctc|"
                          r"compensation|pay)\b", re.I)
MORE = re.compile(r"\b(show more|more results|next page|load more|more jobs|more)\b", re.I)
HELP = re.compile(r"^\s*(hi+|hello|hey|help|thanks|thank you|ok|okay|what can you do\??|who are you\??|\?)"
                  r"[\s!.?]*$", re.I)

RESUME_WORDS = re.compile(r"\b(resume|résumé|cv|ats|skills? gap|missing skills|skills (?:am i|i'm|i am) missing|"
                          r"what skills (?:do i|should i) (?:need|learn)|skills should i learn)\b", re.I)
INTERVIEW_WORDS = re.compile(r"\b(interviews?|mock interview|interview questions?|practice questions)\b", re.I)
TRACK_WORDS = re.compile(r"\b(save|track|bookmark|shortlist|add)\b", re.I)
TRACK_THIS = re.compile(r"^\s*(?:please\s+)?(?:save|track|bookmark|shortlist)\s+(?:it|this|that)"
                        r"(?:\s+(?:one|job))?\W*$", re.I)
APPS = re.compile(r"\b(my applications?|application status|applications? tracker|my tracker|my pipeline|"
                  r"track(?:ing)? my applications|show (?:my )?(?:saved|tracked|applied) jobs|"
                  r"how many (?:jobs )?(?:have i|did i) appl\w*)\b", re.I)

# follow-ups that REMOVE a filter; checked before anything else so "remove the salary filter" isn't a salary question
_ALL_FILTERS = ("city", "min_salary_lpa", "max_experience_years", "work_mode", "notice_period_days")
REMOVALS: list[tuple[re.Pattern, tuple[str, ...]]] = [
    (re.compile(r"\b(?:clear|remove|reset|drop)\s+(?:all\s+)?(?:the\s+)?filters?\b|\bno filters\b", re.I),
     _ALL_FILTERS),
    (re.compile(r"\b(?:remove|drop|clear|ignore|without|forget|no)\b[\w\s]{0,20}\b(?:salary|pay|lpa|ctc|package)\b|"
                r"\bany (?:salary|pay|package)\b", re.I), ("min_salary_lpa",)),
    (re.compile(r"\b(?:any ?where|any city|any location|all cities|all over india|across india|pan[- ]india|"
                r"(?:remove|drop|clear|ignore)\b[\w\s]{0,15}\b(?:city|location))\b", re.I), ("city",)),
    (re.compile(r"\b(?:any experience|(?:remove|drop|clear|ignore)\b[\w\s]{0,15}\bexperience)\b", re.I),
     ("max_experience_years",)),
    (re.compile(r"\b(?:any work mode|not only remote|on-?site is fine|office is fine|"
                r"(?:remove|drop|clear|ignore)\b[\w\s]{0,15}\b(?:remote|hybrid|on-?site|work mode))\b", re.I),
     ("work_mode",)),
    (re.compile(r"\b(?:any notice|(?:remove|drop|clear|ignore)\b[\w\s]{0,15}\bnotice)\b", re.I),
     ("notice_period_days",)),
]

# words to strip before reading a role out of resume/interview requests
_TOOL_WORDS = re.compile(r"\b(resume|résumé|cv|ats|review|check|score|improve|analy[sz]e|rate|feedback|interviews?|"
                         r"mock|prepare|preparation|prep|practice|questions?|ready|round|technical|hr|gap|skills?|"
                         r"missing|lacking|compare|against|match|matching|fit|good|enough|me|us|ask|asked|likely|"
                         r"common|typical|need|learn|should|am|i'm|help|get|an?|tips?|advice|guide|how|crack|"
                         r"clear)\b", re.I)
_AT_COMPANY = re.compile(r"\b(?:at|with)\s+(?P<name>[A-Z][\w&.\-]*(?:\s+[A-Z][\w&.\-]*){0,3})")

_ORDINALS = {"first": 0, "1st": 0, "second": 1, "2nd": 1, "third": 2, "3rd": 2, "fourth": 3, "4th": 3,
             "fifth": 4, "5th": 4, "sixth": 5, "6th": 5, "seventh": 6, "7th": 6, "eighth": 7, "8th": 7,
             "ninth": 8, "9th": 8, "tenth": 9, "10th": 9, "last": -1}
ORDINAL_REF = re.compile(
    r"(?:\b(?P<word>first|1st|second|2nd|third|3rd|fourth|4th|fifth|5th|sixth|6th|seventh|7th|eighth|8th|"
    r"ninth|9th|tenth|10th|last)\s+(?:one|job|company|result|listing|option|role|employer)|"
    r"(?:#|number\s+|no\.?\s*)(?P<num>[1-9]|10)\b)", re.I)

_COMPANY_PATTERNS = [
    re.compile(r"(?:tell me (?:more )?about|info(?:rmation)? (?:on|about)|details (?:on|of|about)|"
               r"research|know about|what do you know about|overview of|insights? (?:on|about|into))\s+"
               r"(?:the\s+)?(?:company\s+)?(?P<name>.+)", re.I),
    re.compile(r"(?:what(?:'s| is) it like|how(?:'s| is) it|how is life)\s+(?:working|to work)\s+(?:at|for|in)\s+"
               r"(?P<name>.+)", re.I),
    re.compile(r"^(?:is|how is|how's)\s+(?P<name>.+?)\s+(?:a good|good|as an employer|to work for|for freshers|"
               r"for (?:a )?career|a nice|a great)", re.I),
    re.compile(r"^(?P<name>.+?)\s+(?:company (?:details|info|profile|overview|review)|as an employer)\s*\??$", re.I),
]
_NAME_TRAILING = re.compile(r"\s+(?:company|ltd\.?|limited|pvt\.?|private|like|please|as an employer|for me|"
                            r"for freshers|india)\s*$", re.I)


@dataclass
class Route:
    intent: Intent
    confident: bool = True
    company: str | None = None
    job_ref: dict | None = None  # the earlier job an ordinal ("the second one") points to
    params: SearchParams | None = None
    role: str | None = None
    notes: list[str] = field(default_factory=list)


def removals(message: str) -> set[str]:
    fields: set[str] = set()
    for pat, names in REMOVALS:
        if pat.search(message):
            fields.update(names)
    return fields


def role_and_company(message: str) -> tuple[str | None, str | None]:
    """'prepare me for a Python developer interview at Infosys' -> ('python developer', 'Infosys')."""
    company = None
    if m := _AT_COMPANY.search(message):
        company = clean_company_name(m.group("name"))
        message = message.replace(m.group(0), " ")
    role = parse_query(_TOOL_WORDS.sub(" ", message)).keywords
    return (role or None), company


def clean_company_name(raw: str) -> str | None:
    name = re.sub(r"[?.!,;]+$", "", raw.strip())
    for _ in range(3):
        name = _NAME_TRAILING.sub("", name).strip()
    name = re.sub(r"^(?:the|a|an)\s+", "", name, flags=re.I).strip(" ,.")
    if not name or len(name) > 40 or len(name.split()) > 5 or JOB_WORDS.search(name) or SALARY_WORDS.search(name):
        return None
    if re.fullmatch(r"(it|this|that|them|this company|that company|you)", name, re.I):
        return None
    return name


def extract_company(message: str) -> str | None:
    for pat in _COMPANY_PATTERNS:
        if m := pat.search(message.strip()):
            if name := clean_company_name(m.group("name")):
                return name
    return None


def resolve_job_ref(message: str, last_jobs: list[dict]) -> dict | None:
    if not last_jobs or not (m := ORDINAL_REF.search(message)):
        return None
    idx = _ORDINALS[m.group("word").lower()] if m.group("word") else int(m.group("num")) - 1
    if idx >= len(last_jobs):
        return None
    return last_jobs[idx]


def merge_refinement(last: SearchParams, message: str, parsed: SearchParams,
                     remove: set[str] | None = None) -> SearchParams:
    update = {k: v for k, v in parsed.model_dump(exclude={"keywords", "page"}).items() if v is not None}
    page = last.page + 1 if (MORE.search(message) and not update and not remove) else 1
    # a removed filter stays removed unless the message sets a *different* value ("not only remote" drops it;
    # "remove remote, show hybrid" keeps hybrid)
    cleared = {k: None for k in (remove or set()) if update.get(k) in (None, getattr(last, k))}
    update = {k: v for k, v in update.items() if k not in cleared}
    return last.model_copy(update={**update, **cleared, "page": min(page, 10)})


def route(message: str, *, last_params: SearchParams | None = None, last_jobs: list[dict] | None = None,
          default_keywords: str | None = None) -> Route:
    msg = message.strip()
    if HELP.match(msg):
        return Route("help")

    parsed = parse_query(msg)

    # 0. "remove the salary filter", "any city", "clear filters" (a new role means a new search instead)
    if last_params and (gone := removals(msg)):
        stripped = msg
        for pat, _ in REMOVALS:
            stripped = pat.sub(" ", stripped)
        new_role = parse_query(stripped).keywords
        if not new_role or new_role == last_params.keywords.lower():
            return Route("refine_search", params=merge_refinement(last_params, msg, parsed, gone))
    without_ref = ORDINAL_REF.sub(" ", msg)  # "salary of the 2nd job": the ordinal's "job" is not a job search
    salary_q = bool(SALARY_WORDS.search(without_ref)) and not JOB_WORDS.search(without_ref)

    # 1. "the second one / company #3" -> an earlier result
    if ref := resolve_job_ref(msg, last_jobs or []):
        if TRACK_WORDS.search(msg) and not RESUME_WORDS.search(msg):
            return Route("track_application", job_ref=ref)
        if RESUME_WORDS.search(msg):
            return Route("resume_match", job_ref=ref)
        if INTERVIEW_WORDS.search(msg):
            return Route("interview_prep", job_ref=ref, role=ref["title"], company=ref["company"])
        if salary_q:
            city = ref.get("location", "").split(",")[0].strip() or None
            return Route("salary_research", job_ref=ref,
                         params=SearchParams(keywords=ref["title"], city=parsed.city or city,
                                             max_experience_years=parsed.max_experience_years))
        return Route("company_research", company=ref["company"], job_ref=ref)
    if ORDINAL_REF.search(msg):  # "the fifth company" but the last search had fewer results (or none)
        n = len(last_jobs or [])
        note = f"I only have {n} result(s) from the last search." if n else "Run a job search first."
        return Route("help", notes=[note])
    if TRACK_THIS.match(msg):
        return Route("help", notes=["Which one? e.g. 'save the second job'."])
    if APPS.search(msg):
        return Route("applications_status")

    # 1b. resume and interview tools
    if RESUME_WORDS.search(msg):
        role, _ = role_and_company(msg)
        return Route("resume_review", role=role or default_keywords or (last_params.keywords if last_params else None))
    if INTERVIEW_WORDS.search(msg):
        role, company = role_and_company(msg)
        role = role or default_keywords or (last_params.keywords if last_params else None)
        if not role:
            return Route("help", notes=["For which role? e.g. 'interview questions for a data analyst'."])
        return Route("interview_prep", role=role, company=company)

    # 2. salary questions ("salary of X", not "X jobs with salary above 8 LPA")
    if salary_q:
        if not parsed.keywords and last_params:
            parsed = parsed.model_copy(update={"keywords": last_params.keywords,
                                               "city": parsed.city or last_params.city})
        if parsed.keywords:
            return Route("salary_research", params=parsed)
        return Route("help", notes=["Which role? e.g. 'average salary of a data analyst in Pune'."])

    # 3. company questions
    if (company := extract_company(msg)) and not JOB_WORDS.search(company):
        return Route("company_research", company=company)

    # 4. follow-up that only changes filters / asks for more
    has_filter = any(v is not None for v in parsed.model_dump(exclude={"keywords", "page"}).values())
    if not parsed.keywords and last_params and (has_filter or MORE.search(msg)):
        return Route("refine_search", params=merge_refinement(last_params, msg, parsed))

    # 5. new search
    if parsed.keywords:
        return Route("job_search", params=parsed, confident=bool(JOB_WORDS.search(msg)) or len(msg.split()) <= 4)
    if default_keywords and (JOB_WORDS.search(msg) or has_filter):
        return Route("job_search", params=parsed.model_copy(update={"keywords": default_keywords}))

    # nothing matched: confident only if it's clearly a search without a role ("show me jobs") or very short
    return Route("help", confident=bool(JOB_WORDS.search(msg)) or len(msg.split()) < 3)
